BUILDING THE .DEB
-----------------

An xword deb file can be built in Scratchbox, or on a normal Debian
system, or on a Nokia Internet Tablet using PyPackager
(http://khertan.net/softwares/pypackager.php).

Building in Scratchbox, or on a normal Debian-based system, the
process is the same:

(1) Unpack the tar.gz file, or check out the code from subversion

(2) Change into the source directory

(3) Execute dpkg-buildpackage:

    dpkg-buildpackage -rfakeroot -i


Building using PyPackager:

(1) Check out the code from the subversion repository:

    svn checkout https://garage.maemo.org/svn/xword/trunk

(2) Delete all of the .svn subdirectories so they don't get installed
    by the newly generated .deb:

    find trunk/root -name .svn | xargs rm -rf

(3) Start PyPackager and open the file "trunk/debian/xword.pypackager".  To do
    this, click the small Open Folder icon in the lower left corner.  This
    brings up the "Open Project" window.  Navigate to the "trunk/debian/"
    folder and open the "xword.pypackager" file.  

(4) You will now be back in the main PyPackager window.  Select the "General"
    tab if it isn't already selected.  At the bottom of that window you will
    see "Source Folder:".  If you checked out the code to the "/home/user"
    folder, the path in that box is correct.   However, if you checked out the
    code to a different folder, you will need to change this value.  To do
    this, click on the "Open" button and navigate to the "/trunk/root/"
    directory.  You will know you are in the correct folder when you see a
    single folder "usr" in the right pane.  Click the "Open" at the bottom of
    the screen.

(4) Click the build button at the bottom of the window.  It looks like three
    small gears.  The process will take a few seconds and you won't see any
    result window in PyPackager.  Your newly built .deb will be in the "trunk"
    directory.

RUNNING XWORD WITHOUT THE .DEB
------------------------------
If you have python2.5 and pyGTK on another platform (Linux, Windows, Mac OS X),
you can simply check out the code from the subversion respository and run it.

    svn checkout https://garage.maemo.org/svn/xword/trunk/root/usr/

Change into the newly created "usr/bin/" directory and run "xword".
