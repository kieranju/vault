#!/usr/bin/python
# encoding: utf-8

import sys, os, json

from subprocess import Popen, PIPE, CalledProcessError
from workflow import Workflow3, Variables
from workflow.util import run_command

log = None
v = Variables()

# With 1Password session key and a vault item UUID, request info for that item
def main(wf):
	# Get cached 1Password session key
	session_key = wf.stored_data('session_key')
	if session_key is None:
		v.arg = 'Vault authentication has expired or is not valid'
		return
	
	args = wf.args
	op = args[0]
	jq = args[1]
	uuid = args[2]
	action = args[3]
	
	# Issue bash command to request item info from 1Password
	item_raw = None
	return_code = 0
	try:
		command_output = Popen([op, 'get', 'item', uuid, '--session', session_key], stdout=PIPE)
		item_raw = run_command([jq, '-a'], stdin=command_output.stdout)
		command_output.wait()
	except CalledProcessError as e:
		return_code = e.returncode
	
	# Error can occur when authentication is not valid
	if item_raw is None:
		v.arg = 'Vault authentication has expired or is not valid'
		return
	
	item = json.loads(item_raw)
	item_fields = item['details']['fields']
	item_field_value = None
	for item_field in item_fields:
		if item_field['name'] == action:
			item_field_value = item_field['value']
			break
	
	# Error can occur when the desired field does not exist
	if not item_field_value or item_field_value is None:
		v.arg = 'Failed to obtain {} for this item'.format(action)
		return
	
	v.arg = 'Sent {} to active window and restored clipboard'.format(action)
	v['value']=item_field_value
	print(v)

if __name__ == '__main__':
	wf = Workflow3()
	log = wf.logger
	sys.exit(wf.run(main))