import os
import json
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from datetime import date, datetime, timedelta
from unanonymize import to_keycounts, find_max_hyp, itter_hypotoses, score_hypo
import json
from shutil import copyfile
import requests

def load_all_ketsets():
    starts,ends =[],[]
    keysets = os.listdir("../exposurekeyset")
    keys = {}
    for keyset in keysets:
        with open(os.path.join("../exposurekeyset",keyset,"data","export.json")) as fp:
            data = json.load(fp)

        enddate = date.fromtimestamp(int(data["endTimestamp"]))
        if enddate not in keys:
            keys[enddate] = []
        keys[enddate].append(data['keys'])
    return keys


def get_all_counts():
    with open("done.json") as fp:
        counts = json.load(fp)

    today = date.today()
    keys = load_all_ketsets()
    for enddate,sets in keys.items():
        if enddate.strftime("%Y-%m-%d") in counts:
            continue
        if enddate == today:
            continue

        total = 0
        for keyset in sets:
            keycounts = to_keycounts(enddate,keyset)
            score,hyp  = find_max_hyp(keycounts)
            total += len(hyp)

        counts[enddate.strftime("%Y-%m-%d")] = total

    with open("res.json","w") as fp:
        json.dump(counts,fp)
    copyfile("res.json","done.json")
    os.remove("res.json")
    #now parse keys again
    return {datetime.strptime(k,"%Y-%m-%d").date() :v for k,v in counts.items()}

def get_sick_data():
    # first get the buildid
    r = requests.get("https://coronadashboard.rijksoverheid.nl/veiligheidsregio/VR04/positief-geteste-mensen")
    html = r.text
    idd = "\"buildId\":\""
    from_buildid = html[html.index(idd)+len(idd):]
    buildid = from_buildid[:from_buildid.index("\"")]

    totals = {}

    for code in ['VR03','VR04','VR05','VR06','VR08']:
        r = requests.get(f"https://coronadashboard.rijksoverheid.nl/_next/data/{buildid}/veiligheidsregio/{code}/positief-geteste-mensen.json")
        data = r.json()

        for day in data['pageProps']['data']['results_per_region']['values']:
            reportdate = date.fromtimestamp(day['date_of_report_unix'])
            if reportdate in totals:
                totals[reportdate] += day['total_reported_increase_per_region']
            else:
                totals[reportdate] = day['total_reported_increase_per_region']

    return totals


TEMPLATE = """
De overheid app "Corona Melder" wordt al een tijdje gebruikt in het oosten van het land, maar door hoeveel mensen eigenlijk? Er komen wel berichten naar buiten over het aantal downloads, maar een app downloaden betekend niet dat je hem ook gebruikt. Deze webpagina verzamelt alle data die door gebruikers van de app geüpload wordt nadat ze positief getest zijn, door te kijken hoeveel dit is kunnen we een inschatting maken van het daadwerkelijke gebruik. We zijn op 5 oktober 2020 begonnen met het verzamelen, omdat de data twee weken beschikbaar blijft hebben we alles vanaf 19 augustus kunnen downloaden. Dit zijn tot nu toe ###NUMBATCH### sets aan data. We kunnen de hoeveelheid geüploadde data vergelijken met het aantal positief geteste personen in de regio om een inschatting te maken van het aantal gebruikers.

In een poging de privacy van de gebruikers te waarborgen word er, als er maar weinig nieuwe echte data is, nep data toegevoegd door de overheid. Echter wordt deze nep data op een manier gegenereerd die deels te onderscheiden is van de echte data. Een korte berekening maakt het mogelijk te schatten hoeveel echte gebruikers hun data hebben geüpload. Hierbij proberen we het aantal te overschatten, zodat we het meest positieve beeld neer zetten.

De afgelopen week lijkt het dat er ###NUMKEYS### zieke gebruikers hun data hebben gedeeld. In de zelfde periode zijn er ###NUMSICK### mensen positief getest in de regio. Dit betekend dat ###PERCENTAGE###% van de mensen in de regio ook echt hun data deeld als ze ziek zijn. Als nogmaals zoveel mensen de app wel gebruiken om gewaarschuwd te worden (en vervolgens in quarantaine gaan), maar niet zelf hun data willen delen, dan zal de app voor ###SOM### van de ontmoetingen een effect kunnen hebben. Dit percentage gaat er wel vanuit de de ontmoeting niet al via andere middellen was gedetecteerd.

We kunnen het gebruik ook over tijd weergeven. Hieronder in het blauw het aantal positieve tests in de regio per dag, en in oranje het aantal uploads.

![Plot van uploads en positieve tests over tijd.](plot_abs.png)

En hier het percentage gebruik over tijd.

![Plot van percentage gebruik over tijd.](plot_rel.png)

Voor onderzoekers en programeurs, er wordt een kopie van de dataset bijgehouden op [github](https://github.com/jorants/CoronaMelderCDN).

"""

if __name__ == "__main__":


    uploadcounts = get_all_counts()
    sick = get_sick_data()

    toreplace = {}
    toreplace["###NUMBATCH###"] = str(len(os.listdir("../exposurekeyset")))


    today = date.today()
    reldays = [d for d in uploadcounts.keys() if 1<(today-d)/timedelta(days=1) <= 8 and d in sick]

    toreplace["###NUMKEYS###"] = str(sum(uploadcounts[d] for d in reldays))
    toreplace["###NUMSICK###"] = str(sum(sick[d] for d in reldays))

    percentage = sum(uploadcounts[d] for d in reldays)/sum(sick[d] for d in reldays)
    toreplace["###PERCENTAGE###"] = str(int(100*percentage+.5))
    toreplace["###SOM###"] = f"{int(100*percentage+.5)}% maal {int(100*percentage*2+.5)}% = {int(200*percentage*percentage+.5)}%"

    res = TEMPLATE
    for k,v in toreplace.items():
        res = res.replace(k,v)

    with open("../docs/index.md","w") as fp:
        fp.write(res)

    relavant_sick = {d:sick[d] for d in uploadcounts if d in sick}
    relavant_counts = {d:uploadcounts[d] for d in relavant_sick}
    T,C = zip(*sorted(relavant_counts.items()))
    T,S = zip(*sorted(relavant_sick.items()))


    fig,ax = plt.subplots()
    ax.set_ylim(0,max(S)*1.1)
    ax.set_ylabel("# Tests en uploads")
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    ax.set_xlabel("Datum")
    ax.plot(T,S)
    ax.plot(T,C)
    plt.savefig("../docs/plot_abs.png", transparent=True)
    ax.cla()

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))

    ax.set_ylabel("% Gebruik")
    ax.set_xlabel("Datum")

    ax.set_ylim(0,100)
    ax.plot(T,[100*c/s for c,s in zip(C,S)])
    plt.savefig("../docs/plot_rel.png", transparent=True)
