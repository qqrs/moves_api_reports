import datetime
import requests
import dateutil.parser
from pprint import pprint
from collections import defaultdict

from moves import MovesClient

import secrets


def main():
    print get_access_token()
    #pprint(daily_places_report())


def get_access_token():
    resp = requests.post('https://api.moves-app.com/oauth/v1/access_token', {
        'grant_type': 'authorization_code',
        'code': secrets.moves['code'],
        'client_id': secrets.moves['client_id'],
        'client_secret': secrets.moves['client_secret'],
        'redirect_uri': 'http://qqrs.github.io/'})
    if resp.status_code != 200:
       print(resp.text)
       raise Exception('Error %s: %s' % (resp.status_code, resp.json()['error']))
    access_token = resp.json()['access_token']
    return access_token


#def broken_get_access_token():
    #moves = MovesClient()
    #access_token = moves.get_oauth_token(secrets.moves['code'])
    #return access_token


def daily_places_report(today=None, month=None):
    if month is None:
        if today is None:
            today = datetime.date.today()
        month = today.strftime('%Y%m')
    moves = MovesClient()
    api_path = 'user/places/daily/%s' % month
    resp = moves.api(api_path, 'GET',
                     params={'access_token': secrets.moves['access_token']})

    stats_defs = {
        'work': {
            'place_names': {'Octopart.com'},
            'stats': {'hours', 'arrive_morning', 'depart_evening'}
        },
        'home': {
            'place_names': {'Home'},
            'stats': {'depart_morning'}
        },
        'gym': {
            'place_names': {
                'Blink Fitness Williamsburg', 'Blink Fitness Chelsea',
                'Blink Fitness Bushwick', 'Blink Fitness Gates'},
            'stats': {'hours'}
        },
    }

    stats = {}
    for day_dict in resp.json():
        (date, day_stats) = extract_daily_place_stats(day_dict, stats_defs)
        if date and day_stats:
            stats[date] = day_stats

    return stats


def extract_daily_place_stats(day, defs):
    date = dateutil.parser.parse(day['date']).date()

    if date.weekday() in (5, 6):        # Skip Sat, Sun
        return (None, None)
    day_places = day['segments'] or []
    place_times = defaultdict(list)
    for v in day_places:
        for place, d in defs.iteritems():
            if v['place'].get('name') in d['place_names']:
                start_time = dateutil.parser.parse(v['startTime'])
                end_time = dateutil.parser.parse(v['endTime'])
                if start_time.date() == date:   # Filter out prev day events.
                    place_times[place].append((start_time, end_time))

    stats = {}
    for place, d in defs.iteritems():
        times = place_times[place]
        for stat_type in d['stats']:
            stat_name = place + '_' + stat_type
            val = get_stat_value_from_times(stat_type, times)
            stats[stat_name] = val or '        '
    return (date, stats)


def get_stat_value_from_times(stat_type, times):
    if stat_type == 'hours':
        # TODO: fix hours across midnight boundaries
        return '%.2f' % sum((t[1] - t[0]).total_seconds() / 3600 for t in times)
    elif stat_type == 'times':
        return ['%s - %s' % (t[0].strftime('%I:%M %p'),
                             t[1].strftime('%I:%M %p'))
                                for t in times]
    elif stat_type == 'arrive_morning':
        return times[0][0].strftime('%I:%M %p') if times else None
    elif stat_type == 'depart_morning':
        return times[0][1].strftime('%I:%M %p') if times else None
    elif stat_type == 'depart_evening':
        return times[-1][1].strftime('%I:%M %p') if times else None
    else:
        raise Exception('Unrecognized stat_type: %s' % stat_type)


if __name__ == '__main__':
    main()
