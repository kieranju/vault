#!/usr/bin/python
# encoding: utf-8

import sys, os, json

from subprocess import Popen, PIPE, CalledProcessError
from workflow import Workflow3
from workflow.util import run_command

# Python2 and Python3 url parse compatibility
try:
	from urllib.parse import urlparse
except ImportError:
	 from urlparse import urlparse

log = None

def fix_url(url):
	p = urlparse(url, 'http')
	if p.netloc:
		netloc = p.netloc
		path = p.path
	else:
		netloc = p.path
		path = ''
	 
	p = p._replace(netloc=netloc, path=path)
	return p.geturl()

# Build Alfred-friendly item list
# TODO: Must distinguish login items vs others, and present modifiers accordingly
def push(wf, items):
	for item in items:
		overview = item.get('overview')
		title = overview.get('title', '').strip()
		tags = ', '.join(overview.get('tags', '')).strip()
		url = overview.get('url', '')
		url = fix_url(url) if url else None
		
		it = wf.add_item(
			title=title, 
			subtitle=tags,
			arg=item.get('uuid'),
			autocomplete=title,
			valid=True,
			uid=item.get('uuid'),
			quicklookurl=url,
			match=u'{} {}'.format(title, tags)
		)
		
		feedback = it.add_modifier(
			key='cmd',
			subtitle='Send username to active window',
			arg=item.get('uuid'),
			valid=True
		)
		feedback.setvar('field', 'username')
		
		feedback = it.add_modifier(
			key='alt',
			subtitle='Send password to active window',
			arg=item.get('uuid'),
			valid=True
		)
		feedback.setvar('field', 'password')
		
		feedback = it.add_modifier(
			key='shift',
			subtitle='Navigate to \'{}\''.format(url) if url else None,
			arg=url,
			valid=True
		)
		feedback.setvar('field', 'url')

# With 1Password session key, obtain an insensitive list of all 1Password vault items
# Insensitive list of vault items are cached for a maximum of 30 seconds to avoid redundant requests to the 1Password API
# Sensitive items such as the email and password are not cached, but are instead copied to the clipboard on a need-to-know basis
# Actioning a vault item with modifiers "cmd" or "alt" will request and copy the email and password separately
def main(wf):
	items_raw = wf.cached_data('items', data_func=None, max_age=30)
	
	# Get cached data if stale
	if items_raw is not None:
		items = json.loads(items_raw)
		push(wf, items)
		return wf.send_feedback()
	
	# Get cached 1Password session key
	session_key = wf.stored_data('session_key')
	if session_key is None:
		it = wf.add_item(
			title='Vault authentication has expired or is not valid', 
			subtitle='Run \'Sign in\' Vault command in Alfred',
			arg='op signin',
			valid=True
		)
		it.setvar('authenticated', '0')
		return wf.send_feedback()
	
	args = wf.args
	op = args[0]
	jq = args[1]
	
	# Issue bash command to request list of items from 1Password
	return_code = 0
	try:
		prompt = Popen(['echo', session_key], stdout=PIPE)
		command_output = Popen([op, 'list', 'items'], stdin=prompt.stdout, stdout=PIPE)
		prompt.stdout.close()
		items_raw = run_command([jq, '-a'], stdin=command_output.stdout)
		command_output.wait()
	except CalledProcessError as e:
		return_code = e.returncode
	
	# Error can occur when the user does not have any vault items
	if items_raw is None:
		wf.add_item(
			title='No items found in vault',
			valid=False,
		)
		return wf.send_feedback()
	
	try:
		items = json.loads(items_raw)
	except ValueError as e:
		# Error can occur when authentication has expired
		it = wf.add_item(
			title='Vault authentication has expired or is not valid',
			subtitle='Run \'Sign in\' Vault command in Alfred',
			arg='op signin',
			valid=True
		)
		it.setvar('authenticated', '0')
		return wf.send_feedback()
	
	push(wf, items)
	wf.send_feedback()
	wf.cache_data('items', items_raw)

if __name__ == '__main__':
	wf = Workflow3()
	log = wf.logger
	sys.exit(wf.run(main))