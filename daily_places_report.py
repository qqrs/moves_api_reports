from moves import MovesClient
import requests
import dateutil.parser
from pprint import pprint, pformat
from collections import defaultdict
import smtplib
import email.utils
from email.mime.text import MIMEText

import secrets


def main():
    #print get_access_token()
    daily_places_report()


def get_access_token():
    resp = requests.post('https://api.moves-app.com/oauth/v1/access_token', {
        'grant_type': 'authorization_code',
        'code': secrets.code,
        'client_id': secrets.client_id,
        'client_secret': secrets.client_secret,
        'redirect_uri': 'http://qqrs.github.io/'})
    if resp.status_code != 200:
       print(resp.text)
       raise Exception('Error %s: %s' % (resp.status_code, resp.json()['error']))
    access_token = resp.json()['access_token']
    return access_token


#def broken_get_access_token():
    #moves = MovesClient()
    #access_token = moves.get_oauth_token(secrets.code)
    #return access_token


def daily_places_report(month='201606'):
    moves = MovesClient()
    api_path = 'user/places/daily/%s' % month
    resp = moves.api(api_path, 'GET',
                     params={'access_token': secrets.access_token})

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
            'place_names': {'24 Hour Fitness', 'Calexico Cart'},
            'stats': {'hours'}
        },
    }

    lines = []
    for day in resp.json():
        stats = extract_daily_place_stats(day, stats_defs)
        if stats:
            #pprint(stats, width=240)
            lines.append(pformat(stats, width=240))
        else:
            #print('---')
            lines.append('---')

    buf = '\n'.join(lines)
    print(buf)
    send_email('daily report', buf)


def extract_daily_place_stats(day, defs):
    date = dateutil.parser.parse(day['date'])
    if date.weekday() in (5, 6):        # Skip Sat, Sun
        return None
    day_places = day['segments'] or []
    place_times = defaultdict(list)
    for v in day_places:
        for place, d in defs.iteritems():
            if v['place'].get('name') in d['place_names']:
                place_times[place].append(
                    (dateutil.parser.parse(v['startTime']),
                     dateutil.parser.parse(v['endTime'])))

    stats = {
        'date': date.strftime('%a %m-%d-%Y'),
    }

    for place, d in defs.iteritems():
        times = place_times[place]
        for stat_type in d['stats']:
            stat_name = place + '_' + stat_type
            val = get_stat_value_from_times(stat_type, times)
            stats[stat_name] = val or '        '
    return stats


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


def send_email(subject, body, recipient='qqrsmith@gmail.com'):
    msg = MIMEText('This is the body of the message.')
    msg['To'] = recipient
    msg['From'] = 'dailyreport@gifball.com'
    msg['Subject'] = 'Simple test message'

    server = smtplib.SMTP('localhost')
    #server.set_debuglevel(True) # show communication with the server
    try:
        server.sendmail(msg['From'], [recipient], msg.as_string())
    finally:
        server.quit()


if __name__ == '__main__':
    main()
