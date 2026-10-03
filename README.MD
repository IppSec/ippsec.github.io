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

### Compiling SCSS

Development was done with the VS Code extension [Live Sass Compiler](https://marketplace.visualstudio.com/items?itemName=ritwickdey.live-sass)

Install this extention and use it to update the stylesheets, note that the `.vscode/settings.json` file contains all the settings required for this extension
