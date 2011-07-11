#!/usr/bin/env python2
# If this doesn't run for you, replace python2 with python

###################
# Copyright 2011 Joseph Henrich (jhenrich@constantcontact.com)
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


args = parser.parse_args()

def log_out(opener):
  print("Logging out now")
  try:
    r = opener.open("https://{}{}".format(args.hostname, args.logout_path))
    if r.getcode() != 200:
      print("Got a non 200 back ({}), there may be a session still around.".format(r.getcode()))
  except Exception, e:
    print("We tried to log out, but were unable to, there may be a lingering session...")

if not args.username:
  args.username = raw_input("Please enter your username: ")

passwords = {}
for pass_name in args.password_fields.split(','):
  passwords[pass_name] = getpass.getpass("'"+pass_name+"':")


params = {"username": args.username, "realm": args.realm, "btnSubmit": "Sign In"}
params.update(passwords)
data = urllib.urlencode(params)


cj = cookielib.CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
try:
  r = opener.open("https://{}{}".format(args.hostname, args.login_path), data)
  cookies = cj._cookies
  try:
    session = cookies[args.hostname]['/']['DSID'].value
  except KeyError, e:
    out_file = open("/tmp/juniperncprompt.out", 'w')
    out_file.write(r.read())
    out_file.close()
    print("Couldn't find any cookies for {}, code was {}, body written to {}".format(args.hostname, r.getcode(), out_file.name))
    sys.exit(1)

  command = "{}/ncui -h {} -c DSID={} -f {}".format(args.nc_path, args.hostname, session, args.cert)
  print("Got the session ({}) creating the tunnel now, use Ctrl+C when you are done.".format(session))
  child = pexpect.spawn(command)
  child.expect('Password:')
  child.sendline("")
  while child.isalive():
    #We don't expect the child to die, but we certainly should exit if it does
    time.sleep(1)


  print("Done!")
  log_out(opener)
except Exception, e:
  print("Uh-oh, we got an exception: {} cleaning up now".format(e))
  print(sys.exc_info()[0])
  log_out(opener)
  
except KeyboardInterrupt:
  log_out(opener)

