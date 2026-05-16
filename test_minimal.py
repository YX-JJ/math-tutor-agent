import os, datetime
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_output.txt')
with open(path, 'w', encoding='utf-8') as f:
    f.write(f"OK at {datetime.datetime.now().isoformat()}\n")
    f.write(f"cwd={os.getcwd()}\n")
    f.write(f"file={__file__}\n")
print("Done")
