# Our FLL 2026 Innovation Project


## The Idea

The idea is to create a box in which archaeologists can put smaller artefacts and have them automatically categorised, weighted and 3D scanned.  
For the 3D scanning, we will be using a single camera and capturing the artefact from all angles.  
The photos will be sent to a more capable server which will use a third-party software (and a process called photogrammetry) to convert those images into a single 3D model.  
This will then be sent back to the Pi.

![diagram](/v1-finished/diagram.png)

---

## Directory Structure + Tech Stack

We will have 2 separate devices that will be running different code. One will be the server and one the Pi, as described earlier, and are represented as *local* and *remote*.  
In remote, we have the server subdirectory, and the main application that will be constantly running is `app.py`.

### Remote

---

This is going to:
- Receive zip files full of images from the Pi  
- Store them in `/uploads/` for temporary holding  
- Move them into a directory called `/photogrammetry/`  
- Call the photogrammetry script/function that takes its input files from `/photogrammetry/` and outputs a 3D model to the folder `/downloads/`  
- We will have a `/downloads` endpoint open on the webserver that the Pi can `wget` with the correct authentication key.

---

### Local

---

This will be our client. It will run a local webserver in which the whole system — remote and local — can be accessed.  
It will provide instructions to users on how to use the system and will control the motor, the camera, and the scales.  
It will need to format this data and express it on the local webpage.  
Possibly, if we have time, we...

---

