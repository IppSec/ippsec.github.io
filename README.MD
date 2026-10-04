# ippsec.github.io

## Search Utility

### Updating the dataset

To update the dataset do the following (assuming you have git cli and python3)

```sh
git clone https://github.com/IppSec/ippsec.github.io.git ippsec
# Or you can use the SSH link if you prefer
cd ippsec
python3 yt_crawl.py -g -a [put your api key here]   # or put the key in yt.secret and omit -a
git push
```

To add only recent videos instead of recrawling everything, use `-d 8` for the last eight days or `-l` for just the newest one:

```sh
python3 yt_crawl.py -d 8 -g
git push
```

### Automatic weekly update

`.github/workflows/update-dataset.yml` adds the past week's videos to `dataset.json` and commits them every Saturday at 16:00 UTC. It can also be run by hand from the Actions tab. It needs two repository secrets (Settings → Secrets and variables → Actions): `YOUTUBE_API_KEY` with the YouTube key and `HTB_API_KEY` with the HTB App Token.
