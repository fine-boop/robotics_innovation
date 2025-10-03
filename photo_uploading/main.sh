#!/bin/bash
main(){
    cd photos || exit
    ls | grep -E "\.jpg$|\.jpeg$|\.png$" | zip photos.zip -@
    echo "Uploading photos.zip to server..."
    curl -X POST -F "file=@photos.zip" http://127.0.0.1/uploads/
    echo "Upload complete."
}

main
