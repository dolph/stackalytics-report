import argparse
import datetime
import json

import requests


DEBUG = False

LAUNCHPAD_IDS = [
    'xuhj', 'ankur-gupta-f', 'annegentle', 'alexandra-settle',
    'byron-mccollum', 'bmoss', 'brian-rosmaita', 'kevin-carter', 'daz',
    'wei-d-chen', 'dolph', 'dstanek', 'egle', 'ganesh-mahalingam', 'gus',
    'hemanth-makkapati', 'joshua.hesketh', 'johngarbutt', 'jim-rollenhagen',
    'kennycjohnston', 'ldbragst', 'lianhau-lu', 'loquacity', 'madorn',
    'malini-k-bhandaru', 'manjeet-s-bhatia', 'matt-O', 'rackerhacker',
    'mikalstill', 'john-d-perkins', 'mrda', 'npustchi', 'neillc', 'rnortman',
    'ntpttr', 'jesse-pretorius', 'paul-dardeau', 'paul-e-luse', 'r1chardj0n3s',
    'ronald-de-rose', 'ionosphere80', 'sfinucane', 'shashirekha-j-gundur',
    'sumant-murke', 'amy-marrich', 'steve-lewis', 'o-tony', 'xek',
    'yalei-wang', 'yamahata', 'saisrikiran-mudigonda', 'electrocucaracha',
    'castulo-martinez', 'joshua-l-white'
]

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def format_timestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime(DATETIME_FORMAT)


def compute_date_range(days_ago):
    utc_today = datetime.datetime.utcnow()
    delta = datetime.timedelta(days=days_ago)
    epoch_dt = datetime.datetime(1970, 1, 1)

    end_epoch = int((utc_today - epoch_dt).total_seconds())
    start_epoch = int((utc_today - delta - epoch_dt).total_seconds())
    return start_epoch, end_epoch


def GET(url, params):
    resp = requests.get(url, params=params)
    if DEBUG:
        print('GET %s' % resp.url)
    resp.raise_for_status()
    data = resp.json()
    if DEBUG:
        print(json.dumps(data, sort_keys=True, indent=4))
    return data


def main(args):
    params = dict()
    params['start_date'], params['end_date'] = compute_date_range(
        args.reporting_period)
    data = GET('http://stackalytics.com/api/1.0/stats/engineers', params)

    osic_report = dict()
    for engineer in data['stats']:
        for lp_id in LAUNCHPAD_IDS:
            if lp_id in engineer['id']:
                osic_report[engineer['id']] = engineer

    total_reviews = 0
    total_engineers = 0
    for engineer in osic_report:
        total_engineers += 1
        total_reviews += osic_report[engineer].get('metric')
    print(
        '%(days)d Day Report (%(start)s to %(end)s)\n' % {
            'days': args.reporting_period,
            'start': format_timestamp(params['start_date']),
            'end': format_timestamp(params['end_date']),
        })
    print(
        '* %(e)d engineers did %(r)d code reviews.' % {
            'e': total_engineers,
            'days': args.reporting_period,
            'r': total_reviews})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate a report from Stackalytics on the collaboration '
                    'between two organizations')
    parser.add_argument(
        '--debug', action='store_true', default=False,
        help='Enable debugging output.')
    parser.add_argument(
        '--reporting-period', type=int, default=7,
        help='Period (in days) to report on.')
    args = parser.parse_args()
    DEBUG = args.debug
    main(args)
