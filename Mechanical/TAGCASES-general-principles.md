* Every tag needs a corresponding mechanical case or "adapter" which is used to attach it to one of the tag bases.    This adapter and its corresponding lid are 3d printed in plastic.

* Each  tag base has a "pogopin" array of six pins that must align with the tag on its adapter at the correct height. Adapters all have rectangular cutouts to accomodate this array. In addition, there are small "pin" holes used to align the adapter with the tag base and screw holes used to attach the adapter to the tag base and do support the adapter's lid (more on the lid below).

* Most tag bases have only a single pair of pin holes, although the newest lipo base has a second pair to enable wider adapters.

* A tag fits into a cutout groove on the cooresponding adapter -- the purpose of this groove is to align the tag in the correct location.  In addition, the adapter has a cutout underneath to accomodate the bottom side components on the tag.  The cutout is slightly larger than the tag to allow for manufacturing tolerances, but there is a tension between this extra freedom and alignment with the base pogo pins.  In some adapters, the ledge between the edge of the cutout and the cutout for bottom side components is too narrow.  However the ledge must be narrow enough that it doesn't interfere with the tag components.

* The screw holes the the adapter (not the lid) are sized to allow press fit of a threaded adapter -- the holes on previous adapters are the proper size.  Similarly the pin holes are sized for press fit of alignment pins.  The pin holes on previous adapters are the correct size.

* In addition to the cutout groove, there is also a cutout for batteries on tags utilizing ms621 or ms920 batteries.   The batteries ride on top of the tag.  The minimum thickness of the tag pcb board is 0.4mm.  It is important that there be some positive alignment at the battery end of the pcb board.  For example, the compasstag adapter lacks this positive stop and is difficult to use properly.  The battery cutout should be sized to allow the largest battery (e.g. ms920 for 2.5v tags without regulators on the battery net).  Again there is a tension between the battery groove and proper tag alignment with positive stop.

* Adapters also have a pair of external slots at either end to accomodate harnesses that consist of elastic thread that is placed in the four corner holes on the tag.  Thus these slots should be at least partially aligned with these holes.

* Every adapter has a lid.  The lid has screw holes that align with those on the base, but are sized to fit the screw and not the threaded adapter.   The lid has two end pieces -- on applies pressure on the tag end opposite the battery and the other on the tag above the pogo pins.  For tags with lipo batteries, the battery end must accomodate the thickness of the battery.

* Every adapter for a coin-cell tag also has a second, no-battery lid for testing boards before the cell is attached. It sits lower, with short end pieces bearing on the board itself (see TAGCASE-PROCESS.md, step 6).

* each adapter and its lid have text identifying the adapter type -- on top of the lid "cross bar" (connecting the screw holes) and under the adapter.  The depth and width of this text has been frequently too thin properly print.

* the datasheet for the 855 series pogopins used (double row) is in BoardDesigns/libraries/855-series\ datasheet.pdf

* the footprint supporting the adapter is in:
  * (single pair of pins) BoardDesigns/kicad_libraries/6pin_tagpoints_new_offset.kicad_mod
  * (two sets of pins) BoardDesigns/kicad_libraries/6pin_tagpoints_double_screws.kicad

