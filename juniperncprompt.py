#!/usr/bin/env python2

import sys
import getpass
import argparse
import urllib2, urllib, cookielib
import subprocess
import os

if sys.version_info < (2,7):
  print("Python 2.7 or greater is required")
  sys.exit(0)


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
#print(args)

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

#print("We'll be trying to connect to:\nhostname: {}{} with user: {}, passes: {}, realm: {}".format(args.hostname, args.login_path, args.username, ", ".join(["{}:{}".format(k,v) for k,v in passwords.items()]), args.realm))

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
  print(session)

  params = [args.nc_path+"/ncui", "-h",args.hostname, "-c", "DSID="+session,  "-f",args.cert]
  #print(params)
  #print("")
  print("ncui will ask you for a password... I have no idea *which* one it wants so just hit enter and everything seems to work.  Use Ctrl+C when you are done")
  stream = subprocess.call(params)


  print("Done!")
  log_out(opener)
except Exception, e:
  print("Uh-oh, we got an exception: {} cleaning up now".format(e))
  print(sys.exc_info()[0])
  log_out(opener)
  
except KeyboardInterrupt:
  log_out(opener)




