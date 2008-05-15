BUILDING THE .DEB
-----------------

An xword deb file can be built in Scratchbox, or on a normal Debian system.
The process is as follows:

(1) Unpack the tar.gz file, or check out the code from subversion:

    svn checkout https://garage.maemo.org/svn/xword/trunk/

(2) Change into the source directory (i.e. the one containing the "xword"
    file).

(3) Execute dpkg-buildpackage:

    dpkg-buildpackage -rfakeroot -i

RUNNING XWORD WITHOUT THE .DEB
------------------------------
If you have python2.5 and pyGTK on another platform (Linux, Windows, 
Mac OS X), you can simply check out the code from the subversion respository
and run it.

    svn checkout https://garage.maemo.org/svn/xword/trunk/

Change into the newly created "trunk/" directory.  Then run "./xword".
