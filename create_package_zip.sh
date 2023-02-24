mkdir package
pip install --target package/ -r requirements.txt
cd package
zip -r ../colonist-deployment-package.zip .
cd ..
zip colonist-deployment-package.zip colonist-pii.yml main.py
