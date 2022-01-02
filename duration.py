import isodate
seconds = 0
for i in open('t').readlines():
    seconds = isodate.parse_duration(i.strip()).total_seconds() + seconds

print(seconds)

