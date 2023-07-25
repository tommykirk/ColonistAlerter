mkdir deployment-package
pip install --target deployment-package/ -r requirements.txt
cd deployment-package
zip -r ../colonist-deployment-package.zip .
cd ..
zip colonist-deployment-package.zip colonist-pii.yml main.py
