# Our FLL 2026 Innovation Project
## TODO LIST 
- Design our login, signup and index html files [here](local/localsite/templates/)
- Add user auth, database logic in the app.py [here](local/localsite/)
- Work out photogrammetry software. Your inputs will be a lot of photos in remote/server/photogrammetry, and your code should output a 3d model to remote/server/photogrammetry/



## The Idea

The idea is to create a box in which archaeologists can put smaller artefacts and have them automatically categorised, weighted and 3D scanned.  
For the 3D scanning, we will be using a single camera and capturing the artefact from all angles.  
The photos will be sent to a more capable server which will use a third-party software (and a process called photogrammetry) to convert those images into a single 3D model.  
This will then be sent back to the Pi.

![diagram](diagram.png)

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

# Roles & Responsibilities

## Frontend Dev - Ryan

**Capabilities**
- Good at HTML and CSS  
- JS basics

##TOOD - 
- in `/local/webserver/` create and style login.html and signup.html
---

## Hardware Person

**Capabilities**
- Good with Raspberry Pis/attachments  
- Good with Linux (I know that I’m the only person here that knows Linux but maybe you can learn)  
- Willing to read instruction manuals and be pissed off with nothing working

---

## Photogrammetry Person - Julian

**Capabilities**
- Good understanding of computer systems  
- Fully understands the tech stack  
- Automation with any language – I would recommend Python or Bash

---

## Backend Dev - Joyce

**Capabilities**
- Good understanding of computer systems  
- Fully understands the tech stack  
- SQL knowledge / experience  
- Flask knowledge / experience

---

## Overall Co-ordinator - Julian

**Capabilities**
- Good at programming, understands concepts and languages  
- Im not bothered to write more cuz its just gonna be me
