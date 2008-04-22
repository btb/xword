Since I don't know how to do a "proper" .deb release, I decided to use
PyPackager (http://khertan.net/softwares/pypackager.php).  This runs on
the Nokia Internet Tablet.

Here's how to build xword-x.x.x.deb on your NIT using PyPackager.

(1) Check out the code from the subversion repository:

    svn checkout https://garage.maemo.org/svn/xword/trunk

(2) Delete all of the .svn subdirectories so they don't get installed
    by the newly generated .deb:

    find . -name .svn | xargs rm -rf

(3) Start PyPackager and open the file "trunk/debian/xword.pypackager".  To do
    this, click the small Open Folder icon in the lower left corner.  This
    brings up the "Open Project" window.  Navigate to the "trunk/debian/"
    folder and open the "xword.pypackager" file.  

(4) You will now be back in the main PyPackager window.  Select the "General"
    tab if it isn't already selected.  At the bottom of that window you will
    see "Source Folder:".  The selection there is probably incorrect since you
    may have checked out the subversion code to a different directory.  Click
    on the "Open" button and navigate to the "/trunk/root/" directory.  You
    will know you are in the correct folder when you see a single folder "usr"
    in the right pane.  Click the "Open" at the bottom of the screen.

(4) Click the build button at the bottom of the window.  It looks like three
    small gears.  The process will take a few seconds and you won't see any
    result window in PyPackager.  Your newly built .deb will be in the "trunk"
    directory.
