import functools

import pika
import json
import copy
import asyncio
import aiormq
import requests
from threading import Thread
import json_tools
from pika.exceptions import AMQPConnectionError

from doraemon import db, app, pika
from json.decoder import JSONDecodeError
from doraemon.models import Api, Args, Task, Result


async def main():
	connection = await aiormq.connect("amqp://k12:97S}mLrjun@10.202.80.196/K12")

	channel = await connection.channel()

	deaclare_ok = await channel.queue_declare('k12qa.doraemon.difftask', durable=True)
	consume_ok = await channel.basic_consume(
		deaclare_ok.queue, on_message, no_ack=True
	)


async def on_message(message):
	message = json.loads(message.body)
	task_id = message['task_id']
	api_id = message['api_id']
	app.logger.info(f'processing :{message}')
	uri = message.get('uri')
	args = message.get('args')
	url = uri + '?' + args
	api = Api.query.get(api_id)

	primary = message['primary'] + url
	# secondary = message['secondary'] + url
	candidate = message['candidate'] + url

	headers = {"appid": "109", "user-agent": "Mozilla/5.0"}

	primary_future = asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, primary, headers=headers))
	primary_res = await primary_future

	candidate_future = asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, candidate, headers=headers))
	candidate_res = await candidate_future

	primary_res_time = primary_res.elapsed.total_seconds()
	candidate_res_time = candidate_res.elapsed.total_seconds()
	try:
		primary_result = primary_res.json()
		candidate_result = candidate_res.json()
		order_by = api.order_by
		if order_by:
			primary_order_result = order_it(primary_result, order_by)
			candidate_order_result = order_it(candidate_result, order_by)
			primary_result = primary_order_result if primary_order_result else primary_result
			candidate_result = candidate_order_result if candidate_order_result else candidate_result
	# secondary_result = secondary_res.json()
	except JSONDecodeError:
		app.logger.error(f'parse_json_failed: primary:[{primary}], candidate:[{candidate}]')
		app.logger.info('compare_text')
		primary_text = primary_res.text
		candidate_text = candidate_res.text
		if primary_text == candidate_text:
			passed = 1
			diffs = ''
		else:
			passed = 0
			if primary_res.status_code != 200:
				diffs = 'primary_service_error'
			else:
				diffs = 'error'
		primary_status = {"url": primary, "status_code": primary_res.status_code}
		candidate_status = {"url": candidate, "status_code": candidate_res.status_code}
		result = Result(task_id=task_id,
						primary=primary,
						candidate=candidate,
						primary_result=json.dumps(primary_status),
						candidate_result=json.dumps(candidate_status),
						passed=passed,
						diffs=json.dumps(diffs),
						primary_res_time=primary_res_time,
						candidate_res_time=candidate_res_time
						)
		db.session.add(result)
		db.session.commit()
		# ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	if not api:
		app.logger.error(f'api_id : {api_id} does not exists')
		# ch.basic_ack(delivery_tag=method.delivery_tag)
		return

	noises = api.noises  # noises = get_noise(primary_result, secondary_result)
	# diffs = get_diffs(primary_result, candidate_result)
	diffs = get_diffs(primary_result, candidate_result)
	app.logger.info(f'primary:[{primary}], candidate:[{candidate}]')

	if noises:

		noises = noises.split(',')
		app.logger.info(f'noises: {noises}')
		app.logger.info(f"replaces: {diffs['replace']}")
		new_diffs = []
		for replace in diffs['replace']:
			if replace.split('/')[-1] not in noises:
				new_diffs.append(replace)
		diffs['replace'] = new_diffs
	app.logger.info(f'diffs: {diffs}')
	passed = False if diffs['replace'] or diffs['remove'] else True
	result = Result(task_id=task_id,
					primary=primary,
					candidate=candidate,
					primary_result=json.dumps(primary_result),
					candidate_result=json.dumps(candidate_result),
					passed=passed,
					diffs=json.dumps(diffs),
					primary_res_time=primary_res_time,
					candidate_res_time=candidate_res_time
					)
	app.logger.info('save_result')
	try:
		db.session.add(result)
		db.session.commit()
	except:
		app.logger.error('save_result_failed', exc_info=1)
	# ch.basic_ack(delivery_tag=method.delivery_tag)


async def get_res(url):
	headers = {"appid": "109", "user-agent": "Mozilla/5.0"}
	if str(url).find("ztapi.xdf.cn") > 0 or str(url).find("172.25.70.76") > 0:
		headers = {"appid": "k12app", "user-agent": "Mozilla/5.0",
				   "accessToken": "6d568327-ac5f-476c-bb9d-e97e87dd8056"}
	future = asyncio.get_event_loop().run_in_executor(None, functools.partial(requests.get, url, headers=headers))
	response = await future
	return response


def get_diffs(primary, candidate):
	json_diffs = json_tools.diff(primary, candidate)
	diffs = {
		"replace": [],
		"remove": []
	}
	for diff in json_diffs:
		if 'replace' in diff:
			diffs['replace'].append(diff['replace'])
		elif 'remove' in diff:
			diffs['remove'].append(diff['remove'])
		else:
			continue
	return diffs


def order_it(json_str, order_by):
	try:
		order_by = order_by.strip()
		*keys, order = order_by.split('/')
		keys.remove('')
		app.logger.info(f'keys:{keys}, order:{order}')
		to_order = copy.copy(json_str)
		exec_str = 'json_str'
		for key in keys:
			to_order = to_order.get(key, None)
			exec_str += f"['{key}']"
		to_exec = f"{exec_str} = sorted({to_order}, key=lambda x: x['{order}'])"
		exec(to_exec)
	except:
		app.logger.error(f'order_string_invalid:{order_by}', exc_info=1)
	else:
		return eval('json_str')


def update_noise(api, noises):
	pre_noises = api.noises
	if pre_noises:
		pre_noises = json.loads(pre_noises)
		noises = list(set(noises).union(set(pre_noises)))
	api.noises = json.dumps(noises)
	try:
		db.session.add(api)
		db.session.commit()
	except:
		app.logger.error('update_noise_failed', exc_info=1)


def get_noise(primary, secondary):
	diffs = json_tools.diff(primary, secondary)
	noises = []
	if diffs:
		for diff in diffs:
			noise = diff.get('replace')
			if noise:
				noises.append(noise)
			else:
				return noises
	return noises


class MyThread(Thread):
	def __init__(self, url):
		Thread.__init__(self)
		self.url = url

	def run(self):
		self.result = get_res(self.url)

	def get_result(self):
		return self.result


if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
	loop.run_forever()
