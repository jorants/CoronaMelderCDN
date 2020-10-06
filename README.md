# CoronaMelderCDN
Copy of the data uploaded to the Corona Melder CDN, including parsed exposure keysets

The script `fetch.py` gets the data from the CDN and unpacks the zips.
The `cdn_pb2.py` file was generated using Google's protobuf compiler and should not be changed by hand, it parses the binary files that contain the keys.
The most accessable format for the keys is the generated json files in each of the directories.

The folder `WebsiteGenerator` contains a script that estimates the number of real uploads and generates plots that are hosted on GitHub pages [here](https://jorants.github.io/CoronaMelderCDN/). Even though fake keys are added to the CDN when less than 150 keys are present, this is still possible due to a bad implementation of the fake key generator. The script generates all possible comibinations of symptome start dates and checks whether this is compatible with the observed keys.

Running `make` will fetch the keys, update the website, and push to github.

To use any of the scripts, first install the the requirements. We advise you to make a virtual enviorment first, but when in a hurry you can run `pip3 install --user -r requirements.txt`.

First fetch was on 05-10-2020, subsequent fetches are timestampt bot in the meta date file and in the commit message.
