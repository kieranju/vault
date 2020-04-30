#!/usr/bin/python
# encoding: utf-8

import sys

from subprocess import Popen, PIPE, CalledProcessError
from workflow import Workflow3, Variables
from workflow.util import run_command

log = None
v = Variables()

# Authenticate with 1Password
def sign_in(args):
	op = args[0]
	subdomain = args[2]
	password = args[3]
	
	if not password:
		print('Authentication failed due to empty password')
		return
	
	session_key = None
	return_code = 0
	try:
		prompt = Popen(['echo', password], stdout=PIPE)
		session_key = run_command([op, 'signin', subdomain, '--output', 'raw'], stdin=prompt.stdout)
		prompt.wait()
		session_key = session_key.rstrip()
	except CalledProcessError as e:
		return_code = e.returncode
	
	if return_code is 0 and session_key is not None:
		# Store 1Password session key
		wf.store_data('session_key', session_key)
		if wf.stored_data('session_key') is None:
			print('Authentication successful, but failed to store session key')
			return
		print('Authentication successful')
		return
	
	if return_code is 145:
		print('Authentication failed due to incorrect password')
		return
	
	print('Authentication failed due to unknown error')

# Invalidate authentication with 1Password, clearing it from the store
def sign_out(args):
	op = args[0]
	
	session_key = wf.stored_data('session_key')
	if session_key is None:
		print('Already signed out')
		return
	
	# Destroy authentication with 1Password
	return_code = 0
	try:
		run_command([op, 'signout', '--session={}'.format(session_key)])
	except CalledProcessError as e:
		return_code = e.returncode
	
	if return_code is 0:
		wf.store_data('session_key', None)
		wf.cache_data('items', None)
		if wf.stored_data('session_key') is not None:
			print('Invalidation successful, but failed to clear session key')
			return
		print('Invalidation successful')
		return
	
	if return_code is 1:
		wf.store_data('session_key', None)
		wf.cache_data('items', None)
		if wf.stored_data('session_key') is not None:
			print('Invalidation successful due to expired session, but failed to clear session key')
			return
		print('Invalidation successful due to expired session')
		return
	
	print('Invalidation failed due to unknown error')
		
	log.debug(return_code)
	
def main(wf):
	args = wf.args
	action = args[1]
	
	actions = {
		'signin': sign_in,
		'signout': sign_out
	}
	
	if action in actions:
	    return actions[action](args)
	
	print('Invalid authentication action')

if __name__ == '__main__':
	wf = Workflow3()
	log = wf.logger
	sys.exit(wf.run(main))