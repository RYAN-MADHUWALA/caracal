import re
with open("caracal/cli/cli_audit.py", "r") as f:
    text = f.read()

text = text.replace('("init", "")', '("setup", "init")')
text = text.replace('("db", "init-db")', '("system", "db")')
text = text.replace('("authority", "issue")', '("authority", "mandate")')
text = text.replace('("authority", "validate")', '("authority", "enforce")')

with open("caracal/cli/cli_audit.py", "w") as f:
    f.write(text)
