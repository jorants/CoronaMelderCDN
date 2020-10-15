import gen

data = gen.load_all_keysets()
for k,v in data.items():
    print(k,len(v))
