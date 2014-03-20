.. _pycore-changelog:

Changelog
=========

Version 1.1.1 (2013-03-19)
--------------------------

* Improved error handling.
* Kegbot Server v0.9.18 (or later) is required.
* Fixes a bug introduced in v1.1.0 that could cause flow meter reports on an
  inactive kegboard.

Version 1.1.0 (2014-03-11)
--------------------------

* Pending pours are robustly retried.
* Internal: Redis is now required, replacing the internal "kegnet" protocol
  for event dispatching between daemons.

Version 1.0.2 (2012-10-30)
--------------------------

* Fixed a crash that occurred when starting kegbot_core.

Version 1.0.1 (2012-10-18)
--------------------------

* Fixed a crash when pouring with no keg bound to the tap.

Version 1.0.0 (2012-07-05)
--------------------------

* 1.0.0 release!
* Branched from `Kegbot server repository <https://github.com/Kegbot/kegbot/>`_.

Older version
-------------

Change history for older version can be found in the `Kegbot server repository
<https://github.com/Kegbot/kegbot/>`_.
