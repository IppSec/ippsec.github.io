import requests
import re
import json
import argparse
# import pdb, jsontree # When Debugging

class AcademyEntry:
    # JSON serializey stuff
    date = ""
    title = ""
    link = ""
    description = ""

    def __init__(self, date, title, link, description):
        self.date, self.title, self.link, self.description = date, title, link, description

    def AsJsonSerializable(self):
        return {
            "date": self.date,
            "title": self.title,
            "link": self.link,
            "description": self.description
        }

def parseAcademy():
    output = []
    for line in open('contributions.csv').readlines():
        date,title,link,description = line.split(";")
        entry = AcademyEntry(
            date, title, link, description).AsJsonSerializable()
        output.append(entry)
    return output

def run(api_key, gitCommit, datasetOutputLocation="dataset.json"):
    print("Parsing Academy Courses")
    contributions = []
    output = parseAcademy()
    for x in output:
        contributions.append(x)

    print("Serializing dataset")
    dataset = json.dumps(contributions)
    print("Writing Dataset dataset...")
    with open(datasetOutputLocation, "w") as ds:
        ds.write(dataset)


def parser():
    parser = argparse.ArgumentParser(
        description="Generate the dataset for the web app")
    parser.add_argument(
            '-a','--api_key',
            help="Your API key from the Youtube API", 
            default=False)
    parser.add_argument(
            '--output_file', '-o',
            help="The output path", 
            default="dataset.json")
    parser.add_argument(
        '-g', '--git-commit',
        help="Automatically commit the dataset file to git (uses git cli)", 
        default=False, 
        type=bool)
    args = parser.parse_args()

    run(args.api_key, args.output_file)


if __name__ == "__main__":
    parser()
