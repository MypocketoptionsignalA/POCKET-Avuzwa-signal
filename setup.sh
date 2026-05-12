#!/bin/bash
echo "Cloning Pocket Option API..."
git clone https://github.com/A11ksa/API-Pocket-Option.git temp_api
cd temp_api
pip install .
cd ..
rm -rf temp_api
echo "✅ API installed successfully"
