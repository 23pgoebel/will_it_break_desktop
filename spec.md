# Will it Break?

## Overview
- The product is a Python desktop application built with Tkinter.
- “Will it Break?” is a 2D bridge-design simulator on a 60 ft by 25 ft grid.
- Users place joints and members in Build mode, view the live bridge cost and stability status, and use Test mode to drive or park one of four vehicles across the bridge.
- The app distributes axle loads to deck joints, solves the truss, and updates member colors from brown through yellow and red to black as a member approaches or exceeds its tension or compression capacity.
- It includes a closed-by-default details panel for reactions and signed member forces, a failure state that preserves the bridge and offers Restart, and a success state that allows another vehicle to be tested.

## Platform
- This is a native desktop application launched from `app.py` with Python 3.10 or newer and Tkinter/Tk; it does not require a web browser or third-party Python packages.
- The app is intended to run on Windows, macOS, and Linux desktop systems that provide a graphical session and a Tk installation. On Linux, install the distribution's Tkinter package (commonly `python3-tk`) if it is not included with Python.

## Purpose
- The app will allow users to design and build a a cost effective 2D virtual bridge and drive various vehicles across it. The app will show the cost of the bridge, the stress in each member through color as the vehicles drive across, and a message if the bridge exceeds the allowable stresses.

## Inputs
- User has a 60ft by 25ft grid with a point at every foot to build a bridge using members and joints. Joints may be located on the intersection of the grid where members meet. No joints may be on the bridge except for at every 10ft interval. User chooses which vehicle will drive across their bridge in test mode.
- Give the user the option to park a vehicle at a given location 'x'. This is where the front axle will be
- These vehicles, with axle loads in lb measured back from the front axle. Each axle load is split between the two deck joints on either side of it, with the nearer joint taking more.

    Vehicle	Axles:
    Car	2,000 at 0 ft; 2,000 at 10 ft
    Loaded dump truck	12,000 at 0 ft; 17,000 at 14 ft; 17,000 at 18.5 ft
    Semi (AASHTO HS20 design truck)	8,000 at 0 ft; 32,000 at 14 ft; 32,000 at 28 ft
    Fire engine	20,000 at 0 ft; 27,000 at 17 ft; 27,000 at 21.5 ft
- Include tools to build the bridge including an eraser to click on a member to delete it, an option build with the members, a button to erase the whole bridge, the ability to drag joints to new intersections on the bridge.
- Add a vehicle dropdown for Car, Loaded Dump Truck, Semi, and Fire Engine.
- Add a numeric front-axle position field with a synchronized slider or step buttons.
- Constrain x to the bridge length and account for axle positions that fall outside the 60 ft span.
- Add Park, Drive Across, and Pause/Resume controls.
- Connect each member between two joints and prevent duplicate members.
- Show existing and proposed member lengths in the hint/status area.
- Use click-to-place on allowed intersections and show a live cursor hint.
- Disable placement on the roadway/deck except at the fixed 10 ft deck joints
- Members may attach to existing deck joints, supports, and any snapped existing joint. Pressing Escape during member placement detaches the partially placed member from the chained last joint and requires a new first joint.
- The bridge deck includes exactly six modeled members and seven deck joints. The determination calculation counts these members and joints.
- Deck members and deck joints are permanent: they cannot be deleted, dragged, or cleared. Structural members may connect to any deck joint.
- Vehicles cross until the rear axle passes x = 60 ft, not merely until the front axle reaches the end.
- Build mode includes Undo for bridge edits.
- Vehicle graphics are vehicle-specific: car, loaded dump truck, semi tractor-trailer, and red fire engine.
- The interface states how many additional members are needed for determinacy or how many redundant members are present. Redundant structural members are visually highlighted with a pink dashed style.
- When a member endpoint is clicked within 2 ft of an existing joint, the new endpoint snaps exactly onto that joint and duplicate joints are automatically combined.

## Calculations
- A truss solver using the method of joints as one linear system, with a message instead of numbers when the truss is unstable (it needs members + 3 = 2 × joints, and a system that isn't nearly singular)
    - Member capacities of 90,000 lb in tension and 75,000 lb in compression. In Test mode, members are colored by how close they are to capacity.
- Cost is calculated by multiplying the total number of joints, including the seven bridge-deck joints and supports, by $500, and the total length of all members, including the six bridge-deck members, by $100, then summing the two products.
- Member forces use positive values for tension and negative values for compression.
- Member forces are solved with the method of joints using axial force equilibrium at every joint. Positive member forces are tension; negative member forces are compression.
- Axle loads are calculated every 0.5 ft of vehicle travel and from axle loads only; bridge weight and vehicle weight beyond the listed axle loads are not included.

## Outputs
- The app has only Build mode and Test mode. In Build mode, the user places joints on a 1 ft grid and connects them with members, and a hint on screen says what the next click will do. In Test mode, the drawing tools are hidden and the user picks a vehicle and drives it across.
- A bridge site has deck joints every 10 ft from x = 0 to x = 60, a pin at x = 0, and a roller at x = 60. These joints cannot be moved or deleted.
- Build mode displays and updates the bridge cost, joint count, member count, and structural stability status.
- Test mode displays the selected vehicle, its front-axle position, and whether the bridge is currently safe or has failed. Member forces and utilization values are not displayed on the bridge or beside individual members during Test mode.
- A details panel remains closed by default. It contains separate joint reaction and member force tables, plus labels showing positive as tension and negative as compression. Member forces are reported in pounds.
- The member force table shows each member's maximum force experienced during each selected vehicle crossing. It does not show peak utilization or where that peak occurs.
- In parked mode, the user selects the front-axle position x and the details panel shows the forces for each member at that position. It does not display member force values on the bridge.
- Member colors are the only live stress indication during Test mode: brown indicates a safety factor of at least 2, yellow through red indicates increasing closeness to the applicable tension or compression capacity, and black indicates that the member has exceeded capacity.
- When a member exceeds capacity, the vehicle stops and a visible failure state appears with the message "Your Bridge Failed", the failed member, and a Restart button. Restart returns to Build mode with the previous bridge intact.
- If the vehicle completes a crossing safely, show a success state and provide a button to drive another vehicle. The next vehicle option can return to Test mode with the vehicle selector and position controls available.
- All controls and status messages have keyboard-accessible alternatives, visible focus states, and text descriptions for screen readers.

## Look and feel
- The app opens in a native desktop window in Build mode with the 60 ft by 25 ft grid, bridge deck, 10 ft deck joints, pin support, roller support, and roads on both sides already displayed. The interface is a clean engineering dashboard built with Tkinter widgets and a Tkinter Canvas: the grid is centered, build tools sit in a compact left panel, cost and status readouts sit in a right panel, and the details panel appears below or in a drawer.
- The grid uses light lines, while deck lines, supports, joints, and members use stronger, clearly different lines.
- Build tools use consistent icons paired with text labels or tooltips. The cursor and selected tool visibly indicate placement, member connection, erasing, or joint dragging.
- Normal joints appear as small white circles with black outlines. Fixed supports have distinct pin and roller markers. Hovered or selected joints use a clearly visible highlight.
- Members look like brown wood when they have a safety factor of at least 2. They transition from yellow through bright red as they approach their applicable tension or compression capacity. A member turns black after it exceeds capacity.
- Compression members use a yellow-to-red capacity scale. Tension members use a green-to-blue capacity scale. The deck uses the same tension/compression colors as structural members.
- Members remain brown until their absolute force exceeds 45,000 lb in tension or 37,500 lb in compression (50 percent of the applicable allowable stress).
- The 2D side-view vehicles show two wheels and use scaled dimensions and proportional axle spacing when possible.
- Vehicle motion is smooth and readable. Test mode provides visible Pause/Resume and Park controls.
- Success and failure states use clear banners or dialogs with restrained animation. Failure includes "Your Bridge Failed", the failed member, and a Restart button that returns to Build mode while preserving the bridge.
- The window can be resized; the Tkinter Canvas scales the grid while keeping controls and status readouts usable.
- Normal status hints are brief and unobtrusive. Controls and status messages do not rely on color alone, have keyboard alternatives, visible focus states, and text descriptions for screen readers.

## Validation
- Build a 60 ft Pratt truss, 10 ft tall, with six 10 ft panels and diagonals sloping down toward the center. Park the semi with its front axle at x = 44 ft, compute the reactions by hand, and use the method of sections to compute the forces in the top chord, bottom chord, and diagonal in the panel from x = 20 to 30. 

The answer should be:
- Top Chord: 80,000 lb compression
- Bottom Chord: 70,400 lb tension
- Diagonal 13,576.45 lb tension

### App validation results
- Parked Semi front axle: x = 44 ft
- Pin reaction at x = 0: 41,600 lb vertical
- Roller reaction at x = 60: 30,400 lb vertical
- Top chord in the 20–30 ft panel: 80,000 lb compression
- Bottom chord in the 20–30 ft panel: 70,380.8 lb tension
- Diagonal in the 20–30 ft panel: 13,590.03 lb tension
- Equilibrium check: pin and roller reactions sum to 72,000 lb, equal to the three on-bridge Semi axle loads.

### Additional validation problems

For both problems, use the 60 ft, 10 ft tall, six-panel Pratt reference truss described above. Report top chord, bottom chord, and diagonal forces in the panel from x = 20 to 30 ft.

#### Problem 1 - Heavy Transport

- Applied loads: 20,000 lb at x = 10 ft; 40,000 lb at x = 25 ft; 30,000 lb at x = 50 ft.
- Support reactions: A = 45,000 lb upward; G = 45,000 lb upward.
- Top chord: 75,000.00 lb compression.
- Bottom chord: 70,000.00 lb tension.
- Diagonal: 7,071.07 lb tension.

#### Problem 2 - Asymmetric Traffic

- Applied loads: 15,000 lb at x = 10 ft; 25,000 lb at x = 20 ft; 35,000 lb at x = 30 ft; 10,000 lb at x = 40 ft.
- Support reactions: A = 50,000 lb upward; G = 35,000 lb upward.
- Top chord: 95,000.00 lb compression.
- Bottom chord: 85,000.00 lb tension.
- Diagonal: 14,142.14 lb tension.

### Validation Results

The app solver results below were run on the 60 ft, 10 ft tall, six-panel Pratt reference truss, using members in the x = 20 to 30 ft panel. App forces are signed: negative is compression and positive is tension.

| Problem | Result | Reactions A / G | Top chord | Bottom chord | Diagonal |
|---|---|---:|---:|---:|---:|
| Heavy Transport | Expected | 45,000 / 45,000 lb | 75,000 lb compression | 70,000 lb tension | 7,071.07 lb tension |
| Heavy Transport | App | 45,000 / 45,000 lb | -75,000 lb | +70,000 lb | +7,071.07 lb |
| Asymmetric Traffic | Expected | 50,000 / 35,000 lb | 95,000 lb compression | 85,000 lb tension | 14,142.14 lb tension |
| Asymmetric Traffic | App | 50,000 / 35,000 lb | -95,000 lb | +85,000 lb | +14,142.14 lb |

### New Validation Results

Both problems were rerun with the app solver on the 60 ft, 10 ft tall, six-panel Pratt reference truss. Member forces are for the x = 20 to 30 ft panel. The app reports compression as negative and tension as positive.

| Problem | Check | Expected | Actual | Result |
|---|---|---:|---:|---|
| Heavy Transport | Reaction A | 45,000.00 lb upward | 45,000.00 lb upward | Match |
| Heavy Transport | Reaction G | 45,000.00 lb upward | 45,000.00 lb upward | Match |
| Heavy Transport | Top chord | 75,000.00 lb compression | -75,000.00 lb | Match |
| Heavy Transport | Bottom chord | 70,000.00 lb tension | +70,000.00 lb | Match |
| Heavy Transport | Diagonal | 7,071.07 lb tension | +7,071.07 lb | Match |
| Asymmetric Traffic | Reaction A | 50,000.00 lb upward | 50,000.00 lb upward | Match |
| Asymmetric Traffic | Reaction G | 35,000.00 lb upward | 35,000.00 lb upward | Match |
| Asymmetric Traffic | Top chord | 95,000.00 lb compression | -95,000.00 lb | Match |
| Asymmetric Traffic | Bottom chord | 85,000.00 lb tension | +85,000.00 lb | Match |
| Asymmetric Traffic | Diagonal | 14,142.14 lb tension | +14,142.14 lb | Match |

## Out of scope
- The app will not have any 3D elements
- Members are all made of the same material, no options to change thickness or strength of members will be added
- The app will only contain the test mode and build mode. No other modes will exist.

# Features
- Snap to feature that makes it easier to connect members by automatically merging joints that were placed within a few feet of each other
- Changed colors so that yellow and red mean compression while green and blue mean tension
- Added an undo, delete all, and drag joint buttons






## Added Features

### Save and Open
- The File menu provides Save and Open for project files. Save stores the bridge design and the beam/project parameters: support type, span, section, deflection limit, and loads. Open restores them from the file.
- Project files retain the current bridge joints and members, selected load situation, and vehicle position. The current app uses the fixed pin-and-roller supports and 60 ft span, with uniform bridge members; the deflection limit is project metadata and is not currently calculated by the truss solver.

### Export results
- An Export results button saves a table of calculations for the currently selected and solved load situation, including support reactions and signed member forces.

## Build stages

### 1. Tkinter window layout
- Build the desktop window with Tkinter widgets and a Tkinter Canvas for the grid, deck joints, pin and roller supports, road sections, tool panel, cost/status panel, details drawer, and Test mode controls.
- Check that the layout is readable, the main grid is prominent when the window is resized, and controls are clearly separated from the canvas.

### 2. Build-mode editing
- Build joint placement, member drawing, member erasing, whole-bridge clearing, joint dragging, cursor hints, duplicate-member prevention, proposed-member length hints, live cost, joint/member counts, and stability status.
- Check that joints are allowed only on valid intersections, deck placement follows the 10 ft deck rules, edits update immediately, fixed supports cannot move or delete, and all controls provide keyboard alternatives.

### 3. Truss and stability calculations
- Build axle-load distribution, support reactions, the method-of-joints linear solver, stability and singularity detection, signed tension/compression forces, and 0.5 ft load-envelope calculations.
- Check that invalid bridges return a clear instability message, member forces use positive for tension and negative for compression, and the Pratt-truss semi validation matches the specified reactions and member-force targets.

### 4. Test-mode interaction
- Build the vehicle selector, front-axle position control, Park, Drive Across, and Pause/Resume controls. Add 2D vehicle animation and the brown-to-yellow-to-red-to-black member stress colors.
- Check that vehicle axle positions are constrained and represented every 0.5 ft, movement is readable, member forces are not shown on the bridge or beside members, and the vehicle stops immediately on failure.

### 5. Results, details, and restart flow
- Build the closed-by-default details panel, separate reaction and member force tables, failure banner, success state, Restart control, and Drive Another Vehicle option.
- Check that tables show signed forces in pounds without peak utilization or peak-position data, successful crossings offer another vehicle, and Restart returns to Build mode while preserving the bridge.