#!/bin/bash
main(){
    cd photos || exit
    ls | grep -E "\.jpg$|\.jpeg$|\.png$" | zip photos.zip -@
    echo "Uploading photos.zip to server..."
    curl -X POST -F "file=@photos.zip" http://127.0.0.1:1337/uploads/?key=onfewio4fu3i4gberiuvb4rievbeiruf3eiuferiugferi
    echo "Upload complete."
}

main
