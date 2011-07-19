#!/usr/bin/env python2
# If this doesn't run for you, replace python2 with python

###################
# Copyright 2011 Joseph Henrich (crimsonknave@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#
######################

import sys
import getpass
import argparse
import urllib2, urllib, cookielib
import os
import pexpect
import time
from elementtidy import TidyHTMLTreeBuilder



# The defaults are what my set up expect, change them if you want
parser = argparse.ArgumentParser(description="Set up the vpn tunnel.")
parser.add_argument('hostname', help="The hostname of the vpn server")
parser.add_argument('-u', '--username', default=None)
parser.add_argument('--password-fields', help="What are the password fields required by your vpn site.  Delimited by commas please", default="password,password#2")
parser.add_argument('-r', '--realm', help="What realm are we using.  This will be a hidden field in the web form on the vpn site", default="Active Directory Users")
parser.add_argument('--login-path', help="The path to the login page (What the submit button points to)", default="/dana-na/auth/url_2/login.cgi")
parser.add_argument('--nc-path', help="Where the juniper network connect files are located", default="{}/.juniper_networks/network_connect".format(os.environ["HOME"]))
parser.add_argument('--logout-path', help="The path to the logout call, so we don't leave sessions trailing behind us.", default="/dana-na/auth/url_2/logout.cgi")
parser.add_argument('--cert', help="The location of the cert file to use with ncui", default="{}/.juniper_networks/network_connect/ssl.crt".format(os.environ["HOME"]))
parser.add_argument('--out-file', help="If an error occurs where should the page be written to for review", default="/tmp/juniperncprompt_error.html")


def find_sessions(base, par=None):
  values = [x.text for x in base.getchildren()]
  if values[1:5] == ['Login IP Address', 'Login Time', 'Idle Time', 'Browser']:
    return par

  for child in base.getchildren():
    answer = find_sessions(child, base)
    if answer is not None:
      return answer


def find_by_name(base, name):
  try:
    if dict(base.items())['name'] == name:
      return base
  except KeyError, AttributeError:
    pass

  for child in base.getchildren():
    answer = find_by_name(child, name)
    if answer is not None:
      return answer

def find_session_values(table):
  return [dict(tr.getchildren()[0].getchildren()[0].items()) for tr in table.getchildren()[1:]]

def display_session(table):
  i = 0
  for tr in table.getchildren():
    if i == 0:
      print(u"     "+u"".join([u"{:<30}".format(text) for text in [td.text for td in tr.getchildren()][1:5]]))
    else:
      print(u"{:<3}: ".format(i)+u"".join([u"{:<30}".format(text) for text in [td.text for td in tr.getchildren()][1:5]]))
    i += 1


class JuniperNCPrompt:
  def __init__(self):
    self.args = parser.parse_args()
    if not self.args.username:
      self.get_user()

    self.passwords = self.get_passwords()
    self.data = self.configure_data(self.passwords)

    self.cj = cookielib.CookieJar()
    self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))

  def parse_error(self, html):
    tree = TidyHTMLTreeBuilder.parse(html)
    prefix = '{http://www.w3.org/1999/xhtml}'
    root = tree.getroot()

    self.form = root.find('{}body/{}form'.format(prefix, prefix))
    # Some of the returned html has a blockquote before the form, some don't
    if self.form is None:
      self.form = root.find('{}body/{}blockquote/{}form'.format(*[prefix]*3))
    if self.form is not None:
      fields = dict(self.form.items())
      if fields['name'] == 'frmConfirmation':
        # Existing sessions open
        print("There are existing sessions open")
        #submit = form.find('{}table/{}tr/{}td/{}table/{}tr/{}td/{}table/{}tr/{}td/{}table/{}tr/{}td/{}input'.format(*[prefix]*13))
        submit = find_by_name(self.form, 'btnContinue')
        values = dict(submit.items())
        table = find_sessions(self.form)
        display_session(table)
        if values["value"] == "Close Selected Sessions and Log in":
          self.close_sessions(table, True)
        elif values["value"] == "Log in (and optionally Close Selected Sessions)":
          self.close_sessions(table)
        session = self.get_session()
        if session is not None:
          return session
        else:
          return self.parse_error(self.args.out_file)
      elif fields['name'] == 'frmLogin':
        # Invalid user/pass try again
        print("Invalid user/pass, please try again")
        self.get_user()
        passwords = self.get_passwords()
        self.data = self.configure_data(passwords)
        self.log_in()
        session = self.get_session()
        if session is not None:
          return session
        else:
          return self.parse_error(self.args.out_file)
      elif fields['name'] == 'frmNextToken':
        # Wait till the next token pops up and then enter it
        temp = self.form.find('{}/input'.format(prefix))
        if temp is not None:
          values = dict(temp.items())
          try:
            if values['name'] == 'key':
              key = values['value']
            else:
              print("Unable to find the key for the next token form, either we detected the form incorrectly or somthing went wrong.")
              return
          except KeyError:
            return
          password = getpass("Please enter the next securID token to appear on your fob")
          self.data = self.configure_data({"password":password})
          #self.opener.open("https://{}{}".format(self.args.hostname, self.args.login_path), self.data)
          self.log_in()
          session = self.get_session()


      else:
        # Unknown case, note where the file is so they can see what happened
        print("An unhandled case has come up.  Please view the page at {}".format(self.args.out_file))
    else:
      print("Unable to parse the html, please view it at {}".format(self.args.out_file))

  def close_sessions(self, table, required=False):
    if required:
      reply = raw_input("Sessions maxed out, select at least one to close (space delimited)")
    else:
      reply = raw_input("Close any sessions you wish to, or log in with out closing sessions by typing 'n' (space delimited)")
      if reply.strip() == 'n':
        reply = ""

    try:
      to_close = [int(x)-1 for x in reply.split()]
    except ValueError:
      reply = False
      display_session(table)
      self.close_sessions(table, required)

    button = dict(find_by_name(self.form, "btnContinue").items())
    form_data_str = dict(find_by_name(self.form, "FormDataStr").items())

    sessions = [dict(tr.getchildren()[0].getchildren()[0].items()) for tr in table.getchildren()[1:]]
    sessions_to_close = [(x['name'], x['value']) for x in [sessions[y] for y in to_close]]
    print("Closing {} which turns out to be {}".format(to_close, sessions_to_close))
    if to_close:
      # We want the FormDataStr to be the last parameter
      base_data = [(button['name'], button['value'])]
      base_data.extend(sessions_to_close)
      base_data.append((form_data_str['name'], form_data_str['value']))
    else:
      base_data = [(button['name'],button['value']), (form_data_str['name'],form_data_str['value'])]
    print base_data
    self.data = urllib.urlencode(base_data)
    print self.data
    print type(self.data)
    self.log_in()

    



  def log_out(self):
    print("Logging out now")
    try:
      self.latest_response = self.opener.open("https://{}{}".format(self.args.hostname, self.args.logout_path))
      if self.latest_response.getcode() != 200:
        print("Got a non 200 back ({}), there may be a session still around.".format(self.latest_response.getcode()))
    except Exception, e:
      print("We tried to log out, but were unable to, there may be a lingering session...")

  def get_passwords(self):
    passwords = {}
    for pass_name in self.args.password_fields.split(','):
      passwords[pass_name] = getpass.getpass("'"+pass_name+"':")
    return passwords

  def get_user(self):
    self.args.username = raw_input("Please enter your username: ")

  def log_in(self):
    self.latest_response = self.opener.open("https://{}{}".format(self.args.hostname, self.args.login_path), self.data)

  def get_session(self):
    cookies = self.cj._cookies
    try:
      session = cookies[self.args.hostname]['/']['DSID'].value
      return session
    except KeyError, e:
      out_file = open(self.args.out_file, 'w')
      out_file.write(self.latest_response.read())
      out_file.close()
      session = self.parse_error(self.args.out_file)
      if session:
        return session
      else:
        print("Couldn't find any cookies for {}, code was {}, body written to {}".format(self.args.hostname, self.latest_response.getcode(), self.args.out_file))
        sys.exit(1)

  def run_ncui(self, session):
    command = "{}/ncui -h {} -c DSID={} -f {}".format(self.args.nc_path, self.args.hostname, session, self.args.cert)
    print("Got the session ({}) creating the tunnel now, use Ctrl+C when you are done.".format(session))
    child = pexpect.spawn(command)
    child.expect('Password:')
    child.sendline("")
    while child.isalive():
      #We don't expect the child to die, but we certainly should exit if it does
      time.sleep(1)

  def configure_data(self, passwords):
    # By not putting this in the __init__ method we don't risk something wonky
    # happening and we have extra password fields from one time to another
    # This is only likly to happen if this is imported as a module
    params = {"username": self.args.username, "realm": self.args.realm, "btnSubmit": "Sign In"}
    params.update(passwords)
    return urllib.urlencode(params)


if __name__ == "__main__":
  try:
    attempt = JuniperNCPrompt()

    attempt.log_in()
    session = attempt.get_session()
    attempt.run_ncui(session)


    print("Done!")
    attempt.log_out()
  except Exception, e:
    print("Uh-oh, we got an exception: {} cleaning up now".format(e))
    print(sys.exc_info()[0])
    attempt.log_out()
    
  except KeyboardInterrupt:
    attempt.log_out()

