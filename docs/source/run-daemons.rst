Run Daemons
===========

Before you begin
----------------

Although it doesn't need to be running on the same machine, you need to have a
Kegbot Server set up for reporting drinks.  After all, Kegbot Core needs
something to talk to.  Refer to the `Kegbot Server Guide
<http://kegbot.org/docs/server/>`_ if necessary.

Common Options
--------------

Each Kegbot program supports some common flags on the command line, in
particular:

**--help**
  Shows complete help for the program, including common options.

**--helpshort**
  Shows a subset of *--help*, just local options.

**--[no]daemon**
  Run (or don't run) as a background daemon. Default ``false``.

**--[no]verbose**
  Log lots of debugging information.

There are many more flags; for more information, see the output of *--help*.

Run Kegbot Core
---------------

There are two important parameters that should be provided to Kegbot Core:

**--api_url**
  The URL of your Kegbot Server, for example,
  ``--api_url=http://localhost:8000/api/``

**--api_key**
  The API key for authenticating to your Kegbot Server.

Armed with the correct values for these, give it a try.  Open up a new terminal
and run the program::

  (pycore) $ kegbot_core.py --api_url=http://localhost:8000/api/ --api_key=100000012345678
  2012-06-21 23:06:34,705 INFO     (main) Kegbot is starting up.
  2012-06-21 23:06:34,710 INFO     (main) Querying backend liveness.
  2012-06-21 23:06:34,938 INFO     (main) Backend appears to be alive.
  2012-06-21 23:06:34,939 INFO     (main) Found 2 taps, adding to tap manager.
  2012-06-21 23:06:34,939 INFO     (tap-manager) Registering new tap: kegboard.flow0
  2012-06-21 23:06:34,939 INFO     (tap-manager) Registering new tap: kegboard.flow1
  2012-06-21 23:06:34,939 INFO     (main) Starting all service threads.
  2012-06-21 23:06:34,939 INFO     (main) starting thread "service-thread"
  2012-06-21 23:06:34,939 INFO     (main) starting thread "net-thread"
  2012-06-21 23:06:34,940 INFO     (main) starting thread "watchdog-thread"
  2012-06-21 23:06:34,940 INFO     (net-thread) network thread started
  2012-06-21 23:06:34,940 INFO     (kegnet) Starting server on ('localhost', 9805)
  2012-06-21 23:06:34,940 INFO     (main) starting thread "eventhub-thread"
  2012-06-21 23:06:34,941 INFO     (main) starting thread "heartbeat-thread"
  2012-06-21 23:06:34,941 INFO     (main) All threads started.

Awesome!  Your core is now running.  It's now time to connect the Kegboard Daemon to it.

Run Kegboard Daemon
-------------------

Connect your Kegboard to your machine.  (Need to build a Kegboard? See
the `Kegboard Guide <http://kegbot.org/docs/kegboard/>`_).

By default, this daemon looks for a USB device at ``/dev/ttyUSB0``, but on a Mac
or with multiple devices attached you may need to use something different.
Specify it with **--kegboard_device**.

Open a second terminal and run the daemon in the foreground::

  (pycore) $ kegboard_daemon.py --kegboard_device=/dev/cu.usbmodemfd131
  2012-06-21 23:10:37,881 INFO     (main) Starting all service threads.
  2012-06-21 23:10:37,881 INFO     (main) starting thread "kegnet"
  2012-06-21 23:10:37,881 INFO     (kegnet) Connecting to localhost:9805
  2012-06-21 23:10:37,881 INFO     (main) starting thread "kegboard-manager"
  2012-06-21 23:10:37,881 INFO     (kegboard-manager) Starting main loop.
  2012-06-21 23:10:37,882 INFO     (main) starting thread "device-io"
  2012-06-21 23:10:37,882 INFO     (device-io) Starting reader loop...
  2012-06-21 23:10:37,882 INFO     (main) All threads started.
  2012-06-21 23:10:37,883 INFO     (main) Running generic main loop (going to sleep).
  2012-06-21 23:10:37,883 INFO     (kegnet) Connected!
  2012-06-21 23:10:40,321 INFO     (device-io) Found a Kegboard! Firmware version 10
  2012-06-21 23:10:40,347 INFO     (kegboard-manager) RX: <HelloMessage: firmware_version=10>

You can see the program has connected to port 9805, the Kegbot Core, on the
local machine, and has found a Kegboard.  Back in the Core terminal, you should
see a new message logging the connection::

  2012-06-21 23:10:37,884 INFO     (kegnet) Remote host connected: 127.0.0.1:65447


If you have a temperature sensor connected, you will see those messages in logs,
too.  Finally, and most importantly, activity on the flow meter inputs will now
be reported to the Kegbot Core and start the flow processing logic.

Run Extras
----------

There are a few extra accessory programs shipping with Pycore.

**kegboard-tester.py**
  A standalone program that tests toggles the relays on a Kegboard in a loop.
  Do not use unless you are testing a board.

**kegboard_monitor.py**
  A standalone program which just prints Kegboard messages without any further
  reporting.

**lcd_daemon.py**
  A program for managing a serial character LCD, displaying pour information
  during a pour.

**rfid_daemon.py**
  An authentication program, which reads RFID tags from a Phidgets RFID reader
  and reports them to Kegbot Core as authentication tokens.

**sound_server.py**
  A program which listens for active flows and plays sounds at certain events.

**test_flow.py**
  A test program which simulates a pour by sending a sequence of events to the
  core.  Use it if you'd like to test the rest of your system without needing a
  Kegboard or flow meter.

Consult the *--help* documentation for information about these programs.

Run in background
-----------------

So far we've covered running the Pycore applications in the foreground.  But
once you've got your system all setup, you'll probably want your Linux box to
run all the daemons automatically.

An excellent and widely used third-party process monitor is
`Supervisor <http://supervisord.org/>`_. Here's a sample configuration file
you can use with it::

  ### Supervisor.conf for pycore
  
  [program:kegbot_core]
  command=su -l pi -c '/usr/local/bin/kegbot_core.py --api_url=http://localhost:8000/api --api_key=f00bar'
  directory=/home/pi
  autostart=true
  autorestart=true
  redirect_stderr=true

For other options, consult the Supervisor docs.
