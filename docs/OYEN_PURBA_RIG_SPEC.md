# Oyen Purba 3D Rig Specification

## Identity

Oyen Purba is the permanent main character of the Oyen YouTube animation pipeline.

Official palette:

- Blaze Orange `#E8842A`
- Sun Cream `#F7D89B`
- Deep Cocoa `#4A2C24`
- Amber Eyes `#D79223`
- Leaf Tail `#2F7D70`

Required design details:

- short, chubby orange tabby proportions;
- large amber eyes;
- cream muzzle, paws, chest, and belly;
- small friendly fangs;
- fang necklace;
- prehistoric loincloth;
- striped articulated tail.

## Rig V1

Rig V1 is a segmented bone-parent armature. Each overlapping character part is rigidly attached to its controlling bone. This avoids unreliable automatic weights on a procedurally assembled mesh and provides a stable editable `.blend` file.

The 28 bones are:

- core: `root`, `pelvis`, `spine`, `chest`, `neck`, `head`, `jaw`;
- face: `ear.L`, `ear.R`, `eye.L`, `eye.R`;
- arms: `upper_arm`, `forearm`, `hand` on both sides;
- legs: `thigh`, `shin`, `foot` on both sides;
- tail: `tail.01` through `tail.05`.

## Motion V1

The prompt influences basic motion:

- walk and run alter travel distance and stride;
- jump adds a root arc;
- surprise opens the jaw and changes head acting;
- smile/laugh animates the jaw;
- anger changes head attitude;
- all clips include body bounce, arm/leg opposition, blinking, ear motion, and a delayed tail wave.

## Rig V2 target

- one clean deformation mesh;
- retopology and UVs;
- weight painting around shoulders, hips, knees, elbows, jaw, and tail;
- IK/FK arms and legs;
- foot roll and ground contacts;
- eye aim control;
- facial shape keys: A, E, I, O, U, M/B/P;
- brows, cheeks, smile, anger, laugh, and blink controls.
