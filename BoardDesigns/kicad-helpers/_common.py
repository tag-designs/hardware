import json, glob
def load(kind):
    return json.load(open(sorted(g for g in glob.glob(f'analysis/*/{kind}.json'))[-1]))
