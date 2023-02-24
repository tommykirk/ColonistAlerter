mkdir package
pip install --target package/ -r requirements.txt
zip -r colonist-deployment-package.zip package/*
zip colonist-deployment-package.zip colonist-pii.yml main.py
