"""
Description: This test is to determine if a single
    instance ONOS 'cluster' can handle a restart

List of test cases:
CASE1: Compile ONOS and push it to the test machines
CASE2: Assign devices to controllers
CASE21: Assign mastership to controllers
CASE3: Assign intents
CASE4: Ping across added host intents
CASE5: Reading state of ONOS
CASE6: The Failure case.
CASE7: Check state after control plane failure
CASE8: Compare topo
CASE9: Link s3-s28 down
CASE10: Link s3-s28 up
CASE11: Switch down
CASE12: Switch up
CASE13: Clean up
CASE14: start election app on all onos nodes
CASE15: Check that Leadership Election is still functional
CASE16: Install Distributed Primitives app
CASE17: Check for basic functionality with distributed primitives
"""


class HAsingleInstanceRestart:

    def __init__( self ):
        self.default = ''

    def CASE1( self, main ):
        """
        CASE1 is to compile ONOS and push it to the test machines

        Startup sequence:
        cell <name>
        onos-verify-cell
        NOTE: temporary - onos-remove-raft-logs
        onos-uninstall
        start mininet
        git pull
        mvn clean install
        onos-package
        onos-install -f
        onos-wait-for-start
        start cli sessions
        start tcpdump
        """
        import imp
        import time
        import json
        main.log.info( "ONOS Single node cluster restart " +
                         "HA test - initialization" )
        main.case( "Setting up test environment" )
        main.caseExplanation = "Setup the test environment including " +\
                                "installing ONOS, starting Mininet and ONOS" +\
                                "cli sessions."

        # load some variables from the params file
        PULLCODE = False
        if main.params[ 'Git' ] == 'True':
            PULLCODE = True
        gitBranch = main.params[ 'branch' ]
        cellName = main.params[ 'ENV' ][ 'cellName' ]

        main.numCtrls = int( main.params[ 'num_controllers' ] )
        if main.ONOSbench.maxNodes:
            if main.ONOSbench.maxNodes < main.numCtrls:
                main.numCtrls = int( main.ONOSbench.maxNodes )

        try:
            from tests.HA.dependencies.HA import HA
            main.HA = HA()
        except Exception as e:
            main.log.exception( e )
            main.cleanup()
            main.exit()

        main.CLIs = []
        main.nodes = []
        ipList = []
        for i in range( 1, int( main.ONOSbench.maxNodes ) + 1 ):
            try:
                main.CLIs.append( getattr( main, 'ONOScli' + str( i ) ) )
                main.nodes.append( getattr( main, 'ONOS' + str( i ) ) )
                ipList.append( main.nodes[ -1 ].ip_address )
            except AttributeError:
                break

        main.step( "Create cell file" )
        cellAppString = main.params[ 'ENV' ][ 'appString' ]
        main.ONOSbench.createCellFile( main.ONOSbench.ip_address, cellName,
                                       main.Mininet1.ip_address,
                                       cellAppString, ipList )
        main.step( "Applying cell variable to environment" )
        cellResult = main.ONOSbench.setCell( cellName )
        verifyResult = main.ONOSbench.verifyCell()

        # FIXME:this is short term fix
        main.log.info( "Removing raft logs" )
        main.ONOSbench.onosRemoveRaftLogs()

        main.log.info( "Uninstalling ONOS" )
        for node in main.nodes:
            main.ONOSbench.onosUninstall( node.ip_address )

        # Make sure ONOS is DEAD
        main.log.info( "Killing any ONOS processes" )
        killResults = main.TRUE
        for node in main.nodes:
            killed = main.ONOSbench.onosKill( node.ip_address )
            killResults = killResults and killed

        cleanInstallResult = main.TRUE
        gitPullResult = main.TRUE

        main.step( "Starting Mininet" )
        # scp topo file to mininet
        # TODO: move to params?
        topoName = "obelisk.py"
        filePath = main.ONOSbench.home + "/tools/test/topos/"
        main.ONOSbench.scp( main.Mininet1,
                            filePath + topoName,
                            main.Mininet1.home,
                            direction="to" )
        mnResult = main.Mininet1.startNet( )
        utilities.assert_equals( expect=main.TRUE, actual=mnResult,
                                 onpass="Mininet Started",
                                 onfail="Error starting Mininet" )

        main.step( "Git checkout and pull " + gitBranch )
        if PULLCODE:
            main.ONOSbench.gitCheckout( gitBranch )
            gitPullResult = main.ONOSbench.gitPull()
            # values of 1 or 3 are good
            utilities.assert_lesser( expect=0, actual=gitPullResult,
                                      onpass="Git pull successful",
                                      onfail="Git pull failed" )
        main.ONOSbench.getVersion( report=True )

        main.step( "Using mvn clean install" )
        cleanInstallResult = main.TRUE
        if PULLCODE and gitPullResult == main.TRUE:
            cleanInstallResult = main.ONOSbench.cleanInstall()
        else:
            main.log.warn( "Did not pull new code so skipping mvn " +
                           "clean install" )
        utilities.assert_equals( expect=main.TRUE,
                                 actual=cleanInstallResult,
                                 onpass="MCI successful",
                                 onfail="MCI failed" )
        # GRAPHS
        # NOTE: important params here:
        #       job = name of Jenkins job
        #       Plot Name = Plot-HA, only can be used if multiple plots
        #       index = The number of the graph under plot name
        job = "HAsingleInstanceRestart"
        plotName = "Plot-HA"
        index = "2"
        graphs = '<ac:structured-macro ac:name="html">\n'
        graphs += '<ac:plain-text-body><![CDATA[\n'
        graphs += '<iframe src="https://onos-jenkins.onlab.us/job/' + job +\
                  '/plot/' + plotName + '/getPlot?index=' + index +\
                  '&width=500&height=300"' +\
                  'noborder="0" width="500" height="300" scrolling="yes" ' +\
                  'seamless="seamless"></iframe>\n'
        graphs += ']]></ac:plain-text-body>\n'
        graphs += '</ac:structured-macro>\n'
        main.log.wiki(graphs)

        main.CLIs = []
        main.nodes = []
        ipList = []
        for i in range( 1, main.numCtrls + 1 ):
            main.CLIs.append( getattr( main, 'ONOScli' + str( i ) ) )
            main.nodes.append( getattr( main, 'ONOS' + str( i ) ) )
            ipList.append( main.nodes[ -1 ].ip_address )

        main.ONOSbench.createCellFile( main.ONOSbench.ip_address, "SingleHA",
                                       main.Mininet1.ip_address,
                                       cellAppString, ipList[ 0 ] )
        cellResult = main.ONOSbench.setCell( "SingleHA" )
        verifyResult = main.ONOSbench.verifyCell()
        main.step( "Creating ONOS package" )
        packageResult = main.ONOSbench.onosPackage()
        utilities.assert_equals( expect=main.TRUE, actual=packageResult,
                                 onpass="ONOS package successful",
                                 onfail="ONOS package failed" )

        main.step( "Installing ONOS package" )
        onosInstallResult = main.TRUE
        for node in main.nodes:
            tmpResult = main.ONOSbench.onosInstall( options="-f",
                                                    node=node.ip_address )
            onosInstallResult = onosInstallResult and tmpResult
        utilities.assert_equals( expect=main.TRUE, actual=onosInstallResult,
                                 onpass="ONOS install successful",
                                 onfail="ONOS install failed" )

        main.step( "Checking if ONOS is up yet" )
        for i in range( 2 ):
            onosIsupResult = main.TRUE
            for node in main.nodes:
                started = main.ONOSbench.isup( node.ip_address )
                if not started:
                    main.log.error( node.name + " hasn't started" )
                onosIsupResult = onosIsupResult and started
            if onosIsupResult == main.TRUE:
                break
        utilities.assert_equals( expect=main.TRUE, actual=onosIsupResult,
                                 onpass="ONOS startup successful",
                                 onfail="ONOS startup failed" )

        main.log.step( "Starting ONOS CLI sessions" )
        cliResults = main.TRUE
        threads = []
        for i in range( main.numCtrls ):
            t = main.Thread( target=main.CLIs[i].startOnosCli,
                             name="startOnosCli-" + str( i ),
                             args=[main.nodes[i].ip_address] )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            cliResults = cliResults and t.result
        utilities.assert_equals( expect=main.TRUE, actual=cliResults,
                                 onpass="ONOS cli startup successful",
                                 onfail="ONOS cli startup failed" )

        # Create a list of active nodes for use when some nodes are stopped
        main.activeNodes = [ i for i in range( 0, len( main.CLIs ) ) ]

        if main.params[ 'tcpdump' ].lower() == "true":
            main.step( "Start Packet Capture MN" )
            main.Mininet2.startTcpdump(
                str( main.params[ 'MNtcpdump' ][ 'folder' ] ) + str( main.TEST )
                + "-MN.pcap",
                intf=main.params[ 'MNtcpdump' ][ 'intf' ],
                port=main.params[ 'MNtcpdump' ][ 'port' ] )

        main.step( "Checking ONOS nodes" )
        nodeResults = utilities.retry( main.HA.nodesCheck,
                                       False,
                                       args=[main.activeNodes],
                                       attempts=5 )

        utilities.assert_equals( expect=True, actual=nodeResults,
                                 onpass="Nodes check successful",
                                 onfail="Nodes check NOT successful" )

        if not nodeResults:
            for i in main.activeNodes:
                cli = main.CLIs[i]
                main.log.debug( "{} components not ACTIVE: \n{}".format(
                    cli.name,
                    cli.sendline( "scr:list | grep -v ACTIVE" ) ) )
            main.log.error( "Failed to start ONOS, stopping test" )
            main.cleanup()
            main.exit()

        main.step( "Activate apps defined in the params file" )
        # get data from the params
        apps = main.params.get( 'apps' )
        if apps:
            apps = apps.split(',')
            main.log.warn( apps )
            activateResult = True
            for app in apps:
                main.CLIs[ 0 ].app( app, "Activate" )
            # TODO: check this worked
            time.sleep( 10 )  # wait for apps to activate
            for app in apps:
                state = main.CLIs[ 0 ].appStatus( app )
                if state == "ACTIVE":
                    activateResult = activeResult and True
                else:
                    main.log.error( "{} is in {} state".format( app, state ) )
                    activeResult = False
            utilities.assert_equals( expect=True,
                                     actual=activateResult,
                                     onpass="Successfully activated apps",
                                     onfail="Failed to activate apps" )
        else:
            main.log.warn( "No apps were specified to be loaded after startup" )

        main.step( "Set ONOS configurations" )
        config = main.params.get( 'ONOS_Configuration' )
        if config:
            main.log.debug( config )
            checkResult = main.TRUE
            for component in config:
                for setting in config[component]:
                    value = config[component][setting]
                    check = main.CLIs[ 0 ].setCfg( component, setting, value )
                    main.log.info( "Value was changed? {}".format( main.TRUE == check ) )
                    checkResult = check and checkResult
            utilities.assert_equals( expect=main.TRUE,
                                     actual=checkResult,
                                     onpass="Successfully set config",
                                     onfail="Failed to set config" )
        else:
            main.log.warn( "No configurations were specified to be changed after startup" )

        main.step( "App Ids check" )
        appCheck = main.TRUE
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].appToIDCheck,
                             name="appToIDCheck-" + str( i ),
                             args=[] )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            appCheck = appCheck and t.result
        if appCheck != main.TRUE:
            node = main.activeNodes[0]
            main.log.warn( main.CLIs[node].apps() )
            main.log.warn( main.CLIs[node].appIDs() )
        utilities.assert_equals( expect=main.TRUE, actual=appCheck,
                                 onpass="App Ids seem to be correct",
                                 onfail="Something is wrong with app Ids" )

    def CASE2( self, main ):
        """
        Assign devices to controllers
        """
        import re
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"

        main.case( "Assigning devices to controllers" )
        main.caseExplanation = "Assign switches to ONOS using 'ovs-vsctl' " +\
                                "and check that an ONOS node becomes the " +\
                                "master of the device."
        main.step( "Assign switches to controllers" )

        ipList = []
        for i in range( main.numCtrls ):
            ipList.append( main.nodes[ i ].ip_address )
        swList = []
        for i in range( 1, 29 ):
            swList.append( "s" + str( i ) )
        main.Mininet1.assignSwController( sw=swList, ip=ipList )

        mastershipCheck = main.TRUE
        for i in range( 1, 29 ):
            response = main.Mininet1.getSwController( "s" + str( i ) )
            try:
                main.log.info( str( response ) )
            except Exception:
                main.log.info( repr( response ) )
            for node in main.nodes:
                if re.search( "tcp:" + node.ip_address, response ):
                    mastershipCheck = mastershipCheck and main.TRUE
                else:
                    main.log.error( "Error, node " + node.ip_address + " is " +
                                    "not in the list of controllers s" +
                                    str( i ) + " is connecting to." )
                    mastershipCheck = main.FALSE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=mastershipCheck,
            onpass="Switch mastership assigned correctly",
            onfail="Switches not assigned correctly to controllers" )

    def CASE21( self, main ):
        """
        Assign mastership to controllers
        """
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        assert main.CLIs, "main.CLIs not defined"
        assert main.nodes, "main.nodes not defined"

        main.case( "Assigning Controller roles for switches" )
        main.caseExplanation = "Check that ONOS is connected to each " +\
                                "device. Then manually assign" +\
                                " mastership to specific ONOS nodes using" +\
                                " 'device-role'"
        main.step( "Assign mastership of switches to specific controllers" )
        # Manually assign mastership to the controller we want
        roleCall = main.TRUE

        ipList = [ ]
        deviceList = []
        onosCli = main.CLIs[ main.activeNodes[0] ]
        try:
            # Assign mastership to specific controllers. This assignment was
            # determined for a 7 node cluser, but will work with any sized
            # cluster
            for i in range( 1, 29 ):  # switches 1 through 28
                # set up correct variables:
                if i == 1:
                    c = 0
                    ip = main.nodes[ c ].ip_address  # ONOS1
                    deviceId = onosCli.getDevice( "1000" ).get( 'id' )
                elif i == 2:
                    c = 1 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS2
                    deviceId = onosCli.getDevice( "2000" ).get( 'id' )
                elif i == 3:
                    c = 1 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS2
                    deviceId = onosCli.getDevice( "3000" ).get( 'id' )
                elif i == 4:
                    c = 3 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS4
                    deviceId = onosCli.getDevice( "3004" ).get( 'id' )
                elif i == 5:
                    c = 2 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS3
                    deviceId = onosCli.getDevice( "5000" ).get( 'id' )
                elif i == 6:
                    c = 2 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS3
                    deviceId = onosCli.getDevice( "6000" ).get( 'id' )
                elif i == 7:
                    c = 5 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS6
                    deviceId = onosCli.getDevice( "6007" ).get( 'id' )
                elif i >= 8 and i <= 17:
                    c = 4 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS5
                    dpid = '3' + str( i ).zfill( 3 )
                    deviceId = onosCli.getDevice( dpid ).get( 'id' )
                elif i >= 18 and i <= 27:
                    c = 6 % main.numCtrls
                    ip = main.nodes[ c ].ip_address  # ONOS7
                    dpid = '6' + str( i ).zfill( 3 )
                    deviceId = onosCli.getDevice( dpid ).get( 'id' )
                elif i == 28:
                    c = 0
                    ip = main.nodes[ c ].ip_address  # ONOS1
                    deviceId = onosCli.getDevice( "2800" ).get( 'id' )
                else:
                    main.log.error( "You didn't write an else statement for " +
                                    "switch s" + str( i ) )
                    roleCall = main.FALSE
                # Assign switch
                assert deviceId, "No device id for s" + str( i ) + " in ONOS"
                # TODO: make this controller dynamic
                roleCall = roleCall and onosCli.deviceRole( deviceId, ip )
                ipList.append( ip )
                deviceList.append( deviceId )
        except ( AttributeError, AssertionError ):
            main.log.exception( "Something is wrong with ONOS device view" )
            main.log.info( onosCli.devices() )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=roleCall,
            onpass="Re-assigned switch mastership to designated controller",
            onfail="Something wrong with deviceRole calls" )

        main.step( "Check mastership was correctly assigned" )
        roleCheck = main.TRUE
        # NOTE: This is due to the fact that device mastership change is not
        #       atomic and is actually a multi step process
        time.sleep( 5 )
        for i in range( len( ipList ) ):
            ip = ipList[i]
            deviceId = deviceList[i]
            # Check assignment
            master = onosCli.getRole( deviceId ).get( 'master' )
            if ip in master:
                roleCheck = roleCheck and main.TRUE
            else:
                roleCheck = roleCheck and main.FALSE
                main.log.error( "Error, controller " + ip + " is not" +
                                " master " + "of device " +
                                str( deviceId ) + ". Master is " +
                                repr( master ) + "." )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=roleCheck,
            onpass="Switches were successfully reassigned to designated " +
                   "controller",
            onfail="Switches were not successfully reassigned" )

    def CASE3( self, main ):
        """
        Assign intents
        """
        import time
        import json
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        # NOTE: we must reinstall intents until we have a persistant intent
        #        datastore!
        main.case( "Adding host Intents" )
        main.caseExplanation = "Discover hosts by using pingall then " +\
                                "assign predetermined host-to-host intents." +\
                                " After installation, check that the intent" +\
                                " is distributed to all nodes and the state" +\
                                " is INSTALLED"

        # install onos-app-fwd
        main.step( "Install reactive forwarding app" )
        onosCli = main.CLIs[ main.activeNodes[0] ]
        installResults = onosCli.activateApp( "org.onosproject.fwd" )
        utilities.assert_equals( expect=main.TRUE, actual=installResults,
                                 onpass="Install fwd successful",
                                 onfail="Install fwd failed" )

        main.step( "Check app ids" )
        appCheck = main.TRUE
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].appToIDCheck,
                             name="appToIDCheck-" + str( i ),
                             args=[] )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            appCheck = appCheck and t.result
        if appCheck != main.TRUE:
            main.log.warn( onosCli.apps() )
            main.log.warn( onosCli.appIDs() )
        utilities.assert_equals( expect=main.TRUE, actual=appCheck,
                                 onpass="App Ids seem to be correct",
                                 onfail="Something is wrong with app Ids" )

        main.step( "Discovering Hosts( Via pingall for now )" )
        # FIXME: Once we have a host discovery mechanism, use that instead
        # REACTIVE FWD test
        pingResult = main.FALSE
        passMsg = "Reactive Pingall test passed"
        time1 = time.time()
        pingResult = main.Mininet1.pingall()
        time2 = time.time()
        if not pingResult:
            main.log.warn("First pingall failed. Trying again...")
            pingResult = main.Mininet1.pingall()
            passMsg += " on the second try"
        utilities.assert_equals(
            expect=main.TRUE,
            actual=pingResult,
            onpass= passMsg,
            onfail="Reactive Pingall failed, " +
                   "one or more ping pairs failed" )
        main.log.info( "Time for pingall: %2f seconds" %
                       ( time2 - time1 ) )
        # timeout for fwd flows
        time.sleep( 11 )
        # uninstall onos-app-fwd
        main.step( "Uninstall reactive forwarding app" )
        node = main.activeNodes[0]
        uninstallResult = main.CLIs[node].deactivateApp( "org.onosproject.fwd" )
        utilities.assert_equals( expect=main.TRUE, actual=uninstallResult,
                                 onpass="Uninstall fwd successful",
                                 onfail="Uninstall fwd failed" )

        main.step( "Check app ids" )
        threads = []
        appCheck2 = main.TRUE
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].appToIDCheck,
                             name="appToIDCheck-" + str( i ),
                             args=[] )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            appCheck2 = appCheck2 and t.result
        if appCheck2 != main.TRUE:
            node = main.activeNodes[0]
            main.log.warn( main.CLIs[node].apps() )
            main.log.warn( main.CLIs[node].appIDs() )
        utilities.assert_equals( expect=main.TRUE, actual=appCheck2,
                                 onpass="App Ids seem to be correct",
                                 onfail="Something is wrong with app Ids" )

        main.step( "Add host intents via cli" )
        intentIds = []
        # TODO: move the host numbers to params
        #       Maybe look at all the paths we ping?
        intentAddResult = True
        hostResult = main.TRUE
        for i in range( 8, 18 ):
            main.log.info( "Adding host intent between h" + str( i ) +
                           " and h" + str( i + 10 ) )
            host1 = "00:00:00:00:00:" + \
                str( hex( i )[ 2: ] ).zfill( 2 ).upper()
            host2 = "00:00:00:00:00:" + \
                str( hex( i + 10 )[ 2: ] ).zfill( 2 ).upper()
            # NOTE: getHost can return None
            host1Dict = onosCli.getHost( host1 )
            host2Dict = onosCli.getHost( host2 )
            host1Id = None
            host2Id = None
            if host1Dict and host2Dict:
                host1Id = host1Dict.get( 'id', None )
                host2Id = host2Dict.get( 'id', None )
            if host1Id and host2Id:
                nodeNum = ( i % len( main.activeNodes ) )
                node = main.activeNodes[nodeNum]
                tmpId = main.CLIs[node].addHostIntent( host1Id, host2Id )
                if tmpId:
                    main.log.info( "Added intent with id: " + tmpId )
                    intentIds.append( tmpId )
                else:
                    main.log.error( "addHostIntent returned: " +
                                     repr( tmpId ) )
            else:
                main.log.error( "Error, getHost() failed for h" + str( i ) +
                                " and/or h" + str( i + 10 ) )
                node = main.activeNodes[0]
                hosts = main.CLIs[node].hosts()
                main.log.warn( "Hosts output: " )
                try:
                    main.log.warn( json.dumps( json.loads( hosts ),
                                               sort_keys=True,
                                               indent=4,
                                               separators=( ',', ': ' ) ) )
                except ( ValueError, TypeError ):
                    main.log.warn( repr( hosts ) )
                hostResult = main.FALSE
        utilities.assert_equals( expect=main.TRUE, actual=hostResult,
                                 onpass="Found a host id for each host",
                                 onfail="Error looking up host ids" )

        intentStart = time.time()
        onosIds = onosCli.getAllIntentsId()
        main.log.info( "Submitted intents: " + str( intentIds ) )
        main.log.info( "Intents in ONOS: " + str( onosIds ) )
        for intent in intentIds:
            if intent in onosIds:
                pass  # intent submitted is in onos
            else:
                intentAddResult = False
        if intentAddResult:
            intentStop = time.time()
        else:
            intentStop = None
        # Print the intent states
        intents = onosCli.intents()
        intentStates = []
        installedCheck = True
        main.log.info( "%-6s%-15s%-15s" % ( 'Count', 'ID', 'State' ) )
        count = 0
        try:
            for intent in json.loads( intents ):
                state = intent.get( 'state', None )
                if "INSTALLED" not in state:
                    installedCheck = False
                intentId = intent.get( 'id', None )
                intentStates.append( ( intentId, state ) )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing intents" )
        # add submitted intents not in the store
        tmplist = [ i for i, s in intentStates ]
        missingIntents = False
        for i in intentIds:
            if i not in tmplist:
                intentStates.append( ( i, " - " ) )
                missingIntents = True
        intentStates.sort()
        for i, s in intentStates:
            count += 1
            main.log.info( "%-6s%-15s%-15s" %
                           ( str( count ), str( i ), str( s ) ) )
        leaders = onosCli.leaders()
        try:
            missing = False
            if leaders:
                parsedLeaders = json.loads( leaders )
                main.log.warn( json.dumps( parsedLeaders,
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
                # check for all intent partitions
                topics = []
                for i in range( 14 ):
                    topics.append( "intent-partition-" + str( i ) )
                main.log.debug( topics )
                ONOStopics = [ j['topic'] for j in parsedLeaders ]
                for topic in topics:
                    if topic not in ONOStopics:
                        main.log.error( "Error: " + topic +
                                        " not in leaders" )
                        missing = True
            else:
                main.log.error( "leaders() returned None" )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing leaders" )
            main.log.error( repr( leaders ) )
        # Check all nodes
        if missing:
            for i in main.activeNodes:
                response = main.CLIs[i].leaders( jsonFormat=False)
                main.log.warn( str( main.CLIs[i].name ) + " leaders output: \n" +
                               str( response ) )

        partitions = onosCli.partitions()
        try:
            if partitions :
                parsedPartitions = json.loads( partitions )
                main.log.warn( json.dumps( parsedPartitions,
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
                # TODO check for a leader in all paritions
                # TODO check for consistency among nodes
            else:
                main.log.error( "partitions() returned None" )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing partitions" )
            main.log.error( repr( partitions ) )
        pendingMap = onosCli.pendingMap()
        try:
            if pendingMap :
                parsedPending = json.loads( pendingMap )
                main.log.warn( json.dumps( parsedPending,
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
                # TODO check something here?
            else:
                main.log.error( "pendingMap() returned None" )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing pending map" )
            main.log.error( repr( pendingMap ) )

        intentAddResult = bool( intentAddResult and not missingIntents and
                                installedCheck )
        if not intentAddResult:
            main.log.error( "Error in pushing host intents to ONOS" )

        main.step( "Intent Anti-Entropy dispersion" )
        for j in range(100):
            correct = True
            main.log.info( "Submitted intents: " + str( sorted( intentIds ) ) )
            for i in main.activeNodes:
                onosIds = []
                ids = main.CLIs[i].getAllIntentsId()
                onosIds.append( ids )
                main.log.debug( "Intents in " + main.CLIs[i].name + ": " +
                                str( sorted( onosIds ) ) )
                if sorted( ids ) != sorted( intentIds ):
                    main.log.warn( "Set of intent IDs doesn't match" )
                    correct = False
                    break
                else:
                    intents = json.loads( main.CLIs[i].intents() )
                    for intent in intents:
                        if intent[ 'state' ] != "INSTALLED":
                            main.log.warn( "Intent " + intent[ 'id' ] +
                                           " is " + intent[ 'state' ] )
                            correct = False
                            break
            if correct:
                break
            else:
                time.sleep(1)
        if not intentStop:
            intentStop = time.time()
        global gossipTime
        gossipTime = intentStop - intentStart
        main.log.info( "It took about " + str( gossipTime ) +
                        " seconds for all intents to appear in each node" )
        gossipPeriod = int( main.params['timers']['gossip'] )
        maxGossipTime = gossipPeriod * len( main.activeNodes )
        utilities.assert_greater_equals(
                expect=maxGossipTime, actual=gossipTime,
                onpass="ECM anti-entropy for intents worked within " +
                       "expected time",
                onfail="Intent ECM anti-entropy took too long. " +
                       "Expected time:{}, Actual time:{}".format( maxGossipTime,
                                                                  gossipTime ) )
        if gossipTime <= maxGossipTime:
            intentAddResult = True

        if not intentAddResult or "key" in pendingMap:
            import time
            installedCheck = True
            main.log.info( "Sleeping 60 seconds to see if intents are found" )
            time.sleep( 60 )
            onosIds = onosCli.getAllIntentsId()
            main.log.info( "Submitted intents: " + str( intentIds ) )
            main.log.info( "Intents in ONOS: " + str( onosIds ) )
            # Print the intent states
            intents = onosCli.intents()
            intentStates = []
            main.log.info( "%-6s%-15s%-15s" % ( 'Count', 'ID', 'State' ) )
            count = 0
            try:
                for intent in json.loads( intents ):
                    # Iter through intents of a node
                    state = intent.get( 'state', None )
                    if "INSTALLED" not in state:
                        installedCheck = False
                    intentId = intent.get( 'id', None )
                    intentStates.append( ( intentId, state ) )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing intents" )
            # add submitted intents not in the store
            tmplist = [ i for i, s in intentStates ]
            for i in intentIds:
                if i not in tmplist:
                    intentStates.append( ( i, " - " ) )
            intentStates.sort()
            for i, s in intentStates:
                count += 1
                main.log.info( "%-6s%-15s%-15s" %
                               ( str( count ), str( i ), str( s ) ) )
            leaders = onosCli.leaders()
            try:
                missing = False
                if leaders:
                    parsedLeaders = json.loads( leaders )
                    main.log.warn( json.dumps( parsedLeaders,
                                               sort_keys=True,
                                               indent=4,
                                               separators=( ',', ': ' ) ) )
                    # check for all intent partitions
                    # check for election
                    topics = []
                    for i in range( 14 ):
                        topics.append( "intent-partition-" + str( i ) )
                    # FIXME: this should only be after we start the app
                    topics.append( "org.onosproject.election" )
                    main.log.debug( topics )
                    ONOStopics = [ j['topic'] for j in parsedLeaders ]
                    for topic in topics:
                        if topic not in ONOStopics:
                            main.log.error( "Error: " + topic +
                                            " not in leaders" )
                            missing = True
                else:
                    main.log.error( "leaders() returned None" )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing leaders" )
                main.log.error( repr( leaders ) )
            # Check all nodes
            if missing:
                for i in main.activeNodes:
                    node = main.CLIs[i]
                    response = node.leaders( jsonFormat=False)
                    main.log.warn( str( node.name ) + " leaders output: \n" +
                                   str( response ) )

            partitions = onosCli.partitions()
            try:
                if partitions :
                    parsedPartitions = json.loads( partitions )
                    main.log.warn( json.dumps( parsedPartitions,
                                               sort_keys=True,
                                               indent=4,
                                               separators=( ',', ': ' ) ) )
                    # TODO check for a leader in all paritions
                    # TODO check for consistency among nodes
                else:
                    main.log.error( "partitions() returned None" )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing partitions" )
                main.log.error( repr( partitions ) )
            pendingMap = onosCli.pendingMap()
            try:
                if pendingMap :
                    parsedPending = json.loads( pendingMap )
                    main.log.warn( json.dumps( parsedPending,
                                               sort_keys=True,
                                               indent=4,
                                               separators=( ',', ': ' ) ) )
                    # TODO check something here?
                else:
                    main.log.error( "pendingMap() returned None" )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing pending map" )
                main.log.error( repr( pendingMap ) )

    def CASE4( self, main ):
        """
        Ping across added host intents
        """
        import json
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        main.case( "Verify connectivity by sending traffic across Intents" )
        main.caseExplanation = "Ping across added host intents to check " +\
                                "functionality and check the state of " +\
                                "the intent"

        onosCli = main.CLIs[ main.activeNodes[0] ]
        main.step( "Check Intent state" )
        installedCheck = True
        # Print the intent states
        intents = main.ONOScli1.intents()
        intentStates = []
        main.log.info( "%-6s%-15s%-15s" % ( 'Count', 'ID', 'State' ) )
        count = 0
        # Iter through intents of a node
        try:
            for intent in json.loads( intents ):
                state = intent.get( 'state', None )
                if "INSTALLED" not in state:
                    installedCheck = False
                intentId = intent.get( 'id', None )
                intentStates.append( ( intentId, state ) )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing intents." )
        # Print states
        intentStates.sort()
        for i, s in intentStates:
            count += 1
            main.log.info( "%-6s%-15s%-15s" %
                           ( str( count ), str( i ), str( s ) ) )
        utilities.assert_equals( expect=True, actual=installedCheck,
                                 onpass="Intents are all INSTALLED",
                                 onfail="Intents are not all in " +
                                        "INSTALLED state" )

        main.step( "Ping across added host intents" )
        PingResult = main.TRUE
        for i in range( 8, 18 ):
            ping = main.Mininet1.pingHost( src="h" + str( i ),
                                           target="h" + str( i + 10 ) )
            PingResult = PingResult and ping
            if ping == main.FALSE:
                main.log.warn( "Ping failed between h" + str( i ) +
                               " and h" + str( i + 10 ) )
            elif ping == main.TRUE:
                main.log.info( "Ping test passed!" )
                # Don't set PingResult or you'd override failures
        if PingResult == main.FALSE:
            main.log.error(
                "Intents have not been installed correctly, pings failed." )
            # TODO: pretty print
            main.log.warn( "ONOS1 intents: " )
            try:
                tmpIntents = onosCli.intents()
                main.log.warn( json.dumps( json.loads( tmpIntents ),
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
            except ( ValueError, TypeError ):
                main.log.warn( repr( tmpIntents ) )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=PingResult,
            onpass="Intents have been installed correctly and pings work",
            onfail="Intents have not been installed correctly, pings failed." )

        main.step( "Check leadership of topics" )
        leaders = onosCli.leaders()
        topicCheck = main.TRUE
        try:
            if leaders:
                parsedLeaders = json.loads( leaders )
                main.log.warn( json.dumps( parsedLeaders,
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
                # check for all intent partitions
                # check for election
                # TODO: Look at Devices as topics now that it uses this system
                topics = []
                for i in range( 14 ):
                    topics.append( "intent-partition-" + str( i ) )
                # FIXME: this should only be after we start the app
                # FIXME: topics.append( "org.onosproject.election" )
                # Print leaders output
                main.log.debug( topics )
                ONOStopics = [ j['topic'] for j in parsedLeaders ]
                for topic in topics:
                    if topic not in ONOStopics:
                        main.log.error( "Error: " + topic +
                                        " not in leaders" )
                        topicCheck = main.FALSE
            else:
                main.log.error( "leaders() returned None" )
                topicCheck = main.FALSE
        except ( ValueError, TypeError ):
            topicCheck = main.FALSE
            main.log.exception( "Error parsing leaders" )
            main.log.error( repr( leaders ) )
            # TODO: Check for a leader of these topics
        # Check all nodes
        if topicCheck:
            for i in main.activeNodes:
                node = main.CLIs[i]
                response = node.leaders( jsonFormat=False)
                main.log.warn( str( node.name ) + " leaders output: \n" +
                               str( response ) )

        utilities.assert_equals( expect=main.TRUE, actual=topicCheck,
                                 onpass="intent Partitions is in leaders",
                                 onfail="Some topics were lost " )
        # Print partitions
        partitions = onosCli.partitions()
        try:
            if partitions :
                parsedPartitions = json.loads( partitions )
                main.log.warn( json.dumps( parsedPartitions,
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
                # TODO check for a leader in all paritions
                # TODO check for consistency among nodes
            else:
                main.log.error( "partitions() returned None" )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing partitions" )
            main.log.error( repr( partitions ) )
        # Print Pending Map
        pendingMap = onosCli.pendingMap()
        try:
            if pendingMap :
                parsedPending = json.loads( pendingMap )
                main.log.warn( json.dumps( parsedPending,
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
                # TODO check something here?
            else:
                main.log.error( "pendingMap() returned None" )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing pending map" )
            main.log.error( repr( pendingMap ) )

        if not installedCheck:
            main.log.info( "Waiting 60 seconds to see if the state of " +
                           "intents change" )
            time.sleep( 60 )
            # Print the intent states
            intents = onosCli.intents()
            intentStates = []
            main.log.info( "%-6s%-15s%-15s" % ( 'Count', 'ID', 'State' ) )
            count = 0
            # Iter through intents of a node
            try:
                for intent in json.loads( intents ):
                    state = intent.get( 'state', None )
                    if "INSTALLED" not in state:
                        installedCheck = False
                    intentId = intent.get( 'id', None )
                    intentStates.append( ( intentId, state ) )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing intents." )
            intentStates.sort()
            for i, s in intentStates:
                count += 1
                main.log.info( "%-6s%-15s%-15s" %
                               ( str( count ), str( i ), str( s ) ) )
            leaders = onosCli.leaders()
            try:
                missing = False
                if leaders:
                    parsedLeaders = json.loads( leaders )
                    main.log.warn( json.dumps( parsedLeaders,
                                               sort_keys=True,
                                               indent=4,
                                               separators=( ',', ': ' ) ) )
                    # check for all intent partitions
                    # check for election
                    topics = []
                    for i in range( 14 ):
                        topics.append( "intent-partition-" + str( i ) )
                    # FIXME: this should only be after we start the app
                    topics.append( "org.onosproject.election" )
                    main.log.debug( topics )
                    ONOStopics = [ j['topic'] for j in parsedLeaders ]
                    for topic in topics:
                        if topic not in ONOStopics:
                            main.log.error( "Error: " + topic +
                                            " not in leaders" )
                            missing = True
                else:
                    main.log.error( "leaders() returned None" )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing leaders" )
                main.log.error( repr( leaders ) )
            if missing:
                for i in main.activeNodes:
                    node = main.CLIs[i]
                    response = node.leaders( jsonFormat=False)
                    main.log.warn( str( node.name ) + " leaders output: \n" +
                                   str( response ) )

            partitions = onosCli.partitions()
            try:
                if partitions :
                    parsedPartitions = json.loads( partitions )
                    main.log.warn( json.dumps( parsedPartitions,
                                               sort_keys=True,
                                               indent=4,
                                               separators=( ',', ': ' ) ) )
                    # TODO check for a leader in all paritions
                    # TODO check for consistency among nodes
                else:
                    main.log.error( "partitions() returned None" )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing partitions" )
                main.log.error( repr( partitions ) )
            pendingMap = onosCli.pendingMap()
            try:
                if pendingMap :
                    parsedPending = json.loads( pendingMap )
                    main.log.warn( json.dumps( parsedPending,
                                               sort_keys=True,
                                               indent=4,
                                               separators=( ',', ': ' ) ) )
                    # TODO check something here?
                else:
                    main.log.error( "pendingMap() returned None" )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing pending map" )
                main.log.error( repr( pendingMap ) )
        # Print flowrules
        node = main.activeNodes[0]
        main.log.debug( main.CLIs[node].flows( jsonFormat=False ) )
        main.step( "Wait a minute then ping again" )
        # the wait is above
        PingResult = main.TRUE
        for i in range( 8, 18 ):
            ping = main.Mininet1.pingHost( src="h" + str( i ),
                                           target="h" + str( i + 10 ) )
            PingResult = PingResult and ping
            if ping == main.FALSE:
                main.log.warn( "Ping failed between h" + str( i ) +
                               " and h" + str( i + 10 ) )
            elif ping == main.TRUE:
                main.log.info( "Ping test passed!" )
                # Don't set PingResult or you'd override failures
        if PingResult == main.FALSE:
            main.log.error(
                "Intents have not been installed correctly, pings failed." )
            # TODO: pretty print
            main.log.warn( "ONOS1 intents: " )
            try:
                tmpIntents = onosCli.intents()
                main.log.warn( json.dumps( json.loads( tmpIntents ),
                                           sort_keys=True,
                                           indent=4,
                                           separators=( ',', ': ' ) ) )
            except ( ValueError, TypeError ):
                main.log.warn( repr( tmpIntents ) )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=PingResult,
            onpass="Intents have been installed correctly and pings work",
            onfail="Intents have not been installed correctly, pings failed." )

    def CASE5( self, main ):
        """
        Reading state of ONOS
        """
        import json
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"

        main.case( "Setting up and gathering data for current state" )
        # The general idea for this test case is to pull the state of
        # ( intents,flows, topology,... ) from each ONOS node
        # We can then compare them with each other and also with past states

        main.step( "Check that each switch has a master" )
        global mastershipState
        mastershipState = '[]'

        # Assert that each device has a master
        rolesNotNull = main.TRUE
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].rolesNotNull,
                             name="rolesNotNull-" + str( i ),
                             args=[] )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            rolesNotNull = rolesNotNull and t.result
        utilities.assert_equals(
            expect=main.TRUE,
            actual=rolesNotNull,
            onpass="Each device has a master",
            onfail="Some devices don't have a master assigned" )

        main.step( "Get the Mastership of each switch" )
        ONOS1Mastership = main.ONOScli1.roles()
        # TODO: Make this a meaningful check
        if "Error" in ONOS1Mastership or not ONOS1Mastership:
            main.log.error( "Error in getting ONOS roles" )
            main.log.warn(
                "ONOS1 mastership response: " +
                repr( ONOS1Mastership ) )
            consistentMastership = main.FALSE
        else:
            mastershipState = ONOS1Mastership
            consistentMastership = main.TRUE

        main.step( "Get the intents from each controller" )
        global intentState
        intentState = []
        ONOS1Intents = main.ONOScli1.intents( jsonFormat=True )
        intentCheck = main.FALSE
        if "Error" in ONOS1Intents or not ONOS1Intents:
            main.log.error( "Error in getting ONOS intents" )
            main.log.warn( "ONOS1 intents response: " + repr( ONOS1Intents ) )
        else:
            intentCheck = main.TRUE

        main.step( "Get the flows from each controller" )
        global flowState
        flowState = []
        flowCheck = main.FALSE
        ONOS1Flows = main.ONOScli1.flows( jsonFormat=True )
        if "Error" in ONOS1Flows or not ONOS1Flows:
            main.log.error( "Error in getting ONOS flows" )
            main.log.warn( "ONOS1 flows repsponse: " + ONOS1Flows )
        else:
            # TODO: Do a better check, maybe compare flows on switches?
            flowState = ONOS1Flows
            flowCheck = main.TRUE

        main.step( "Get the OF Table entries" )
        global flows
        flows = []
        for i in range( 1, 29 ):
            flows.append( main.Mininet1.getFlowTable( "s" + str( i ), version="1.3", debug=False ) )
        if flowCheck == main.FALSE:
            for table in flows:
                main.log.warn( table )
        # TODO: Compare switch flow tables with ONOS flow tables

        main.step( "Collecting topology information from ONOS" )
        devices = []
        devices.append( main.ONOScli1.devices() )
        hosts = []
        hosts.append( json.loads( main.ONOScli1.hosts() ) )
        ports = []
        ports.append( main.ONOScli1.ports() )
        links = []
        links.append( main.ONOScli1.links() )
        clusters = []
        clusters.append( main.ONOScli1.clusters() )

        main.step( "Each host has an IP address" )
        ipResult = main.TRUE
        for controller in range( 0, len( hosts ) ):
            controllerStr = str( main.activeNodes[controller] + 1 )
            if hosts[ controller ]:
                for host in hosts[ controller ]:
                    if not host.get( 'ipAddresses', [ ] ):
                        main.log.error( "Error with host ips on controller" +
                                        controllerStr + ": " + str( host ) )
                        ipResult = main.FALSE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=ipResult,
            onpass="The ips of the hosts aren't empty",
            onfail="The ip of at least one host is missing" )

        # there should always only be one cluster
        main.step( "There is only one dataplane cluster" )
        try:
            numClusters = len( json.loads( clusters[ 0 ] ) )
        except ( ValueError, TypeError ):
            main.log.exception( "Error parsing clusters[0]: " +
                                repr( clusters[ 0 ] ) )
            numClusters = "ERROR"
        clusterResults = main.FALSE
        if numClusters == 1:
            clusterResults = main.TRUE
        utilities.assert_equals(
            expect=1,
            actual=numClusters,
            onpass="ONOS shows 1 SCC",
            onfail="ONOS shows " + str( numClusters ) + " SCCs" )

        main.step( "Comparing ONOS topology to MN" )
        devicesResults = main.TRUE
        linksResults = main.TRUE
        hostsResults = main.TRUE
        mnSwitches = main.Mininet1.getSwitches()
        mnLinks = main.Mininet1.getLinks()
        mnHosts = main.Mininet1.getHosts()
        for controller in main.activeNodes:
            controllerStr = str( main.activeNodes[controller] + 1 )
            if devices[ controller ] and ports[ controller ] and\
                "Error" not in devices[ controller ] and\
                "Error" not in ports[ controller ]:
                    currentDevicesResult = main.Mininet1.compareSwitches(
                            mnSwitches,
                            json.loads( devices[ controller ] ),
                            json.loads( ports[ controller ] ) )
            else:
                currentDevicesResult = main.FALSE
            utilities.assert_equals( expect=main.TRUE,
                                     actual=currentDevicesResult,
                                     onpass="ONOS" + controllerStr +
                                     " Switches view is correct",
                                     onfail="ONOS" + controllerStr +
                                     " Switches view is incorrect" )
            if links[ controller ] and "Error" not in links[ controller ]:
                currentLinksResult = main.Mininet1.compareLinks(
                        mnSwitches, mnLinks,
                        json.loads( links[ controller ] ) )
            else:
                currentLinksResult = main.FALSE
            utilities.assert_equals( expect=main.TRUE,
                                     actual=currentLinksResult,
                                     onpass="ONOS" + controllerStr +
                                     " links view is correct",
                                     onfail="ONOS" + controllerStr +
                                     " links view is incorrect" )

            if hosts[ controller ] and "Error" not in hosts[ controller ]:
                currentHostsResult = main.Mininet1.compareHosts(
                        mnHosts,
                        hosts[ controller ] )
            else:
                currentHostsResult = main.FALSE
            utilities.assert_equals( expect=main.TRUE,
                                     actual=currentHostsResult,
                                     onpass="ONOS" + controllerStr +
                                     " hosts exist in Mininet",
                                     onfail="ONOS" + controllerStr +
                                     " hosts don't match Mininet" )

            devicesResults = devicesResults and currentDevicesResult
            linksResults = linksResults and currentLinksResult
            hostsResults = hostsResults and currentHostsResult

        main.step( "Device information is correct" )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=devicesResults,
            onpass="Device information is correct",
            onfail="Device information is incorrect" )

        main.step( "Links are correct" )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=linksResults,
            onpass="Link are correct",
            onfail="Links are incorrect" )

        main.step( "Hosts are correct" )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=hostsResults,
            onpass="Hosts are correct",
            onfail="Hosts are incorrect" )

    def CASE6( self, main ):
        """
        The Failure case.
        """
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"

        # Reset non-persistent variables
        try:
            iCounterValue = 0
        except NameError:
            main.log.error( "iCounterValue not defined, setting to 0" )
            iCounterValue = 0

        main.case( "Restart ONOS node" )
        main.caseExplanation = "Killing ONOS process and restart cli " +\
                                "sessions once onos is up."

        main.step( "Checking ONOS Logs for errors" )
        for node in main.nodes:
            main.log.debug( "Checking logs for errors on " + node.name + ":" )
            main.log.warn( main.ONOSbench.checkLogs( node.ip_address ) )

        main.step( "Killing ONOS processes" )
        killResult = main.ONOSbench.onosKill( main.nodes[0].ip_address )
        start = time.time()
        utilities.assert_equals( expect=main.TRUE, actual=killResult,
                                 onpass="ONOS Killed",
                                 onfail="Error killing ONOS" )

        main.step( "Checking if ONOS is up yet" )
        count = 0
        while count < 10:
            onos1Isup = main.ONOSbench.isup( main.nodes[0].ip_address )
            if onos1Isup == main.TRUE:
                elapsed = time.time() - start
                break
            else:
                count = count + 1
        utilities.assert_equals( expect=main.TRUE, actual=onos1Isup,
                                 onpass="ONOS is back up",
                                 onfail="ONOS failed to start" )

        main.log.step( "Starting ONOS CLI sessions" )
        cliResults = main.ONOScli1.startOnosCli( main.nodes[0].ip_address )
        utilities.assert_equals( expect=main.TRUE, actual=cliResults,
                                 onpass="ONOS cli startup successful",
                                 onfail="ONOS cli startup failed" )

        if elapsed:
            main.log.info( "ESTIMATE: ONOS took %s seconds to restart" %
                           str( elapsed ) )
            main.restartTime = elapsed
        else:
            main.restartTime = -1
        time.sleep( 5 )
        # rerun on election apps
        main.ONOScli1.electionTestRun()

    def CASE7( self, main ):
        """
        Check state after ONOS failure
        """
        import json
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        main.case( "Running ONOS Constant State Tests" )

        main.step( "Check that each switch has a master" )
        # Assert that each device has a master
        rolesNotNull = main.TRUE
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].rolesNotNull,
                             name="rolesNotNull-" + str( i ),
                             args=[ ] )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            rolesNotNull = rolesNotNull and t.result
        utilities.assert_equals(
            expect=main.TRUE,
            actual=rolesNotNull,
            onpass="Each device has a master",
            onfail="Some devices don't have a master assigned" )

        main.step( "Check if switch roles are consistent across all nodes" )
        ONOS1Mastership = main.ONOScli1.roles()
        # FIXME: Refactor this whole case for single instance
        if "Error" in ONOS1Mastership or not ONOS1Mastership:
            main.log.error( "Error in getting ONOS mastership" )
            main.log.warn( "ONOS1 mastership response: " +
                           repr( ONOS1Mastership ) )
            consistentMastership = main.FALSE
        else:
            consistentMastership = main.TRUE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=consistentMastership,
            onpass="Switch roles are consistent across all ONOS nodes",
            onfail="ONOS nodes have different views of switch roles" )

        description2 = "Compare switch roles from before failure"
        main.step( description2 )

        currentJson = json.loads( ONOS1Mastership )
        oldJson = json.loads( mastershipState )
        mastershipCheck = main.TRUE
        for i in range( 1, 29 ):
            switchDPID = str(
                main.Mininet1.getSwitchDPID( switch="s" + str( i ) ) )

            current = [ switch[ 'master' ] for switch in currentJson
                        if switchDPID in switch[ 'id' ] ]
            old = [ switch[ 'master' ] for switch in oldJson
                    if switchDPID in switch[ 'id' ] ]
            if current == old:
                mastershipCheck = mastershipCheck and main.TRUE
            else:
                main.log.warn( "Mastership of switch %s changed" % switchDPID )
                mastershipCheck = main.FALSE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=mastershipCheck,
            onpass="Mastership of Switches was not changed",
            onfail="Mastership of some switches changed" )
        mastershipCheck = mastershipCheck and consistentMastership

        main.step( "Get the intents and compare across all nodes" )
        ONOS1Intents = main.ONOScli1.intents( jsonFormat=True )
        intentCheck = main.FALSE
        if "Error" in ONOS1Intents or not ONOS1Intents:
            main.log.error( "Error in getting ONOS intents" )
            main.log.warn( "ONOS1 intents response: " + repr( ONOS1Intents ) )
        else:
            intentCheck = main.TRUE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=intentCheck,
            onpass="Intents are consistent across all ONOS nodes",
            onfail="ONOS nodes have different views of intents" )
        # Print the intent states
        intents = []
        intents.append( ONOS1Intents )
        intentStates = []
        for node in intents:  # Iter through ONOS nodes
            nodeStates = []
            # Iter through intents of a node
            for intent in json.loads( node ):
                nodeStates.append( intent[ 'state' ] )
            intentStates.append( nodeStates )
            out = [ (i, nodeStates.count( i ) ) for i in set( nodeStates ) ]
            main.log.info( dict( out ) )

        # NOTE: Store has no durability, so intents are lost across system
        #       restarts
        """
        main.step( "Compare current intents with intents before the failure" )
        # NOTE: this requires case 5 to pass for intentState to be set.
        #      maybe we should stop the test if that fails?
        sameIntents = main.FALSE
        try:
            intentState
        except NameError:
            main.log.warn( "No previous intent state was saved" )
        else:
            if intentState and intentState == ONOSIntents[ 0 ]:
                sameIntents = main.TRUE
                main.log.info( "Intents are consistent with before failure" )
            # TODO: possibly the states have changed? we may need to figure out
            #       what the acceptable states are
            elif len( intentState ) == len( ONOSIntents[ 0 ] ):
                sameIntents = main.TRUE
                try:
                    before = json.loads( intentState )
                    after = json.loads( ONOSIntents[ 0 ] )
                    for intent in before:
                        if intent not in after:
                            sameIntents = main.FALSE
                            main.log.debug( "Intent is not currently in ONOS " +
                                            "(at least in the same form):" )
                            main.log.debug( json.dumps( intent ) )
                except ( ValueError, TypeError ):
                    main.log.exception( "Exception printing intents" )
                    main.log.debug( repr( ONOSIntents[0] ) )
                    main.log.debug( repr( intentState ) )
            if sameIntents == main.FALSE:
                try:
                    main.log.debug( "ONOS intents before: " )
                    main.log.debug( json.dumps( json.loads( intentState ),
                                                sort_keys=True, indent=4,
                                                separators=( ',', ': ' ) ) )
                    main.log.debug( "Current ONOS intents: " )
                    main.log.debug( json.dumps( json.loads( ONOSIntents[ 0 ] ),
                                                sort_keys=True, indent=4,
                                                separators=( ',', ': ' ) ) )
                except ( ValueError, TypeError ):
                    main.log.exception( "Exception printing intents" )
                    main.log.debug( repr( ONOSIntents[0] ) )
                    main.log.debug( repr( intentState ) )
            utilities.assert_equals(
                expect=main.TRUE,
                actual=sameIntents,
                onpass="Intents are consistent with before failure",
                onfail="The Intents changed during failure" )
        intentCheck = intentCheck and sameIntents
        """
        main.step( "Get the OF Table entries and compare to before " +
                   "component failure" )
        FlowTables = main.TRUE
        for i in range( 28 ):
            main.log.info( "Checking flow table on s" + str( i + 1 ) )
            tmpFlows = main.Mininet1.getFlowTable( "s" + str( i + 1 ), version="1.3", debug=False )
            curSwitch = main.Mininet1.flowTableComp( flows[i], tmpFlows )
            FlowTables = FlowTables and curSwitch
            if curSwitch == main.FALSE:
                main.log.warn( "Differences in flow table for switch: s{}".format( i + 1 ) )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=FlowTables,
            onpass="No changes were found in the flow tables",
            onfail="Changes were found in the flow tables" )

        main.step( "Leadership Election is still functional" )
        # Test of LeadershipElection

        leader = main.nodes[ main.activeNodes[ 0 ] ].ip_address
        leaderResult = main.TRUE
        for controller in range( 1, main.numCtrls + 1 ):
            # loop through ONOScli handlers
            node = getattr( main, ( 'ONOScli' + str( controller ) ) )
            leaderN = node.electionTestLeader()
            # verify leader is ONOS1
            # NOTE even though we restarted ONOS, it is the only one so onos 1
            # must be leader
            if leaderN == leader:
                # all is well
                pass
            elif leaderN == main.FALSE:
                # error in response
                main.log.error( "Something is wrong with " +
                                 "electionTestLeader function, check the" +
                                 " error logs" )
                leaderResult = main.FALSE
            elif leader != leaderN:
                leaderResult = main.FALSE
                main.log.error( "ONOS" + str( controller ) + " sees " +
                                 str( leaderN ) +
                                 " as the leader of the election app. " +
                                 "Leader should be " + str( leader ) )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=leaderResult,
            onpass="Leadership election passed",
            onfail="Something went wrong with Leadership election" )

    def CASE8( self, main ):
        """
        Compare topo
        """
        import json
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"

        main.case( "Compare ONOS Topology view to Mininet topology" )
        main.caseExplanation = "Compare topology objects between Mininet" +\
                                " and ONOS"
        topoResult = main.FALSE
        elapsed = 0
        count = 0
        main.step( "Comparing ONOS topology to MN topology" )
        startTime = time.time()
        # Give time for Gossip to work
        while topoResult == main.FALSE and ( elapsed < 60 or count < 3 ):
            devicesResults = main.TRUE
            linksResults = main.TRUE
            hostsResults = main.TRUE
            hostAttachmentResults = True
            count += 1
            cliStart = time.time()
            devices = []
            devices.append( main.ONOScli1.devices() )
            hosts = []
            hosts.append( json.loads( main.ONOScli1.hosts() ) )
            ipResult = main.TRUE
            for controller in range( 0, len( hosts ) ):
                controllerStr = str( controller + 1 )
                for host in hosts[ controller ]:
                    if host is None or host.get( 'ipAddresses', [] ) == []:
                        main.log.error(
                            "DEBUG:Error with host ips on controller" +
                            controllerStr + ": " + str( host ) )
                        ipResult = main.FALSE
            ports = []
            ports.append( main.ONOScli1.ports() )
            links = []
            links.append( main.ONOScli1.links() )
            clusters = []
            clusters.append( main.ONOScli1.clusters() )

            elapsed = time.time() - startTime
            cliTime = time.time() - cliStart
            print "CLI time: " + str( cliTime )

            mnSwitches = main.Mininet1.getSwitches()
            mnLinks = main.Mininet1.getLinks()
            mnHosts = main.Mininet1.getHosts()
            for controller in range( main.numCtrls ):
                controllerStr = str( controller + 1 )
                if devices[ controller ] and ports[ controller ] and\
                    "Error" not in devices[ controller ] and\
                    "Error" not in ports[ controller ]:

                    try:
                        currentDevicesResult = main.Mininet1.compareSwitches(
                                mnSwitches,
                                json.loads( devices[ controller ] ),
                                json.loads( ports[ controller ] ) )
                    except ( TypeError, ValueError ) as e:
                        main.log.exception( "Object not as expected; devices={!r}\nports={!r}".format(
                            devices[ controller ], ports[ controller ] ) )
                else:
                    currentDevicesResult = main.FALSE
                utilities.assert_equals( expect=main.TRUE,
                                         actual=currentDevicesResult,
                                         onpass="ONOS" + controllerStr +
                                         " Switches view is correct",
                                         onfail="ONOS" + controllerStr +
                                         " Switches view is incorrect" )

                if links[ controller ] and "Error" not in links[ controller ]:
                    currentLinksResult = main.Mininet1.compareLinks(
                            mnSwitches, mnLinks,
                            json.loads( links[ controller ] ) )
                else:
                    currentLinksResult = main.FALSE
                utilities.assert_equals( expect=main.TRUE,
                                         actual=currentLinksResult,
                                         onpass="ONOS" + controllerStr +
                                         " links view is correct",
                                         onfail="ONOS" + controllerStr +
                                         " links view is incorrect" )

                if hosts[ controller ] or "Error" not in hosts[ controller ]:
                    currentHostsResult = main.Mininet1.compareHosts(
                            mnHosts,
                            hosts[ controller ] )
                else:
                    currentHostsResult = main.FALSE
                utilities.assert_equals( expect=main.TRUE,
                                         actual=currentHostsResult,
                                         onpass="ONOS" + controllerStr +
                                         " hosts exist in Mininet",
                                         onfail="ONOS" + controllerStr +
                                         " hosts don't match Mininet" )
                # CHECKING HOST ATTACHMENT POINTS
                hostAttachment = True
                zeroHosts = False
                # FIXME: topo-HA/obelisk specific mappings:
                # key is mac and value is dpid
                mappings = {}
                for i in range( 1, 29 ):  # hosts 1 through 28
                    # set up correct variables:
                    macId = "00:" * 5 + hex( i ).split( "0x" )[1].upper().zfill(2)
                    if i == 1:
                        deviceId = "1000".zfill(16)
                    elif i == 2:
                        deviceId = "2000".zfill(16)
                    elif i == 3:
                        deviceId = "3000".zfill(16)
                    elif i == 4:
                        deviceId = "3004".zfill(16)
                    elif i == 5:
                        deviceId = "5000".zfill(16)
                    elif i == 6:
                        deviceId = "6000".zfill(16)
                    elif i == 7:
                        deviceId = "6007".zfill(16)
                    elif i >= 8 and i <= 17:
                        dpid = '3' + str( i ).zfill( 3 )
                        deviceId = dpid.zfill(16)
                    elif i >= 18 and i <= 27:
                        dpid = '6' + str( i ).zfill( 3 )
                        deviceId = dpid.zfill(16)
                    elif i == 28:
                        deviceId = "2800".zfill(16)
                    mappings[ macId ] = deviceId
                if hosts[ controller ] or "Error" not in hosts[ controller ]:
                    if hosts[ controller ] == []:
                        main.log.warn( "There are no hosts discovered" )
                        zeroHosts = True
                    else:
                        for host in hosts[ controller ]:
                            mac = None
                            location = None
                            device = None
                            port = None
                            try:
                                mac = host.get( 'mac' )
                                assert mac, "mac field could not be found for this host object"

                                location = host.get( 'location' )
                                assert location, "location field could not be found for this host object"

                                # Trim the protocol identifier off deviceId
                                device = str( location.get( 'elementId' ) ).split(':')[1]
                                assert device, "elementId field could not be found for this host location object"

                                port = location.get( 'port' )
                                assert port, "port field could not be found for this host location object"

                                # Now check if this matches where they should be
                                if mac and device and port:
                                    if str( port ) != "1":
                                        main.log.error( "The attachment port is incorrect for " +
                                                        "host " + str( mac ) +
                                                        ". Expected: 1 Actual: " + str( port) )
                                        hostAttachment = False
                                    if device != mappings[ str( mac ) ]:
                                        main.log.error( "The attachment device is incorrect for " +
                                                        "host " + str( mac ) +
                                                        ". Expected: " + mappings[ str( mac ) ] +
                                                        " Actual: " + device )
                                        hostAttachment = False
                                else:
                                    hostAttachment = False
                            except AssertionError:
                                main.log.exception( "Json object not as expected" )
                                main.log.error( repr( host ) )
                                hostAttachment = False
                else:
                    main.log.error( "No hosts json output or \"Error\"" +
                                    " in output. hosts = " +
                                    repr( hosts[ controller ] ) )
                if zeroHosts is False:
                    hostAttachment = True

                devicesResults = devicesResults and currentDevicesResult
                linksResults = linksResults and currentLinksResult
                hostsResults = hostsResults and currentHostsResult
                hostAttachmentResults = hostAttachmentResults and\
                                        hostAttachment

            # "consistent" results don't make sense for single instance
            # there should always only be one cluster
            clusterResults = main.FALSE
            try:
                numClusters = len( json.loads( clusters[ 0 ] ) )
            except ( ValueError, TypeError ):
                main.log.exception( "Error parsing clusters[0]: " +
                                    repr( clusters[0] ) )
                numClusters = "ERROR"
                clusterResults = main.FALSE
            if numClusters == 1:
                clusterResults = main.TRUE
            utilities.assert_equals(
                expect=1,
                actual=numClusters,
                onpass="ONOS shows 1 SCC",
                onfail="ONOS shows " + str( numClusters ) + " SCCs" )

            topoResult = ( devicesResults and linksResults
                           and hostsResults and ipResult and clusterResults and
                           hostAttachmentResults )

        topoResult = topoResult and int( count <= 2 )
        note = "note it takes about " + str( int( cliTime ) ) + \
            " seconds for the test to make all the cli calls to fetch " +\
            "the topology from each ONOS instance"
        main.log.info(
            "Very crass estimate for topology discovery/convergence( " +
            str( note ) + " ): " + str( elapsed ) + " seconds, " +
            str( count ) + " tries" )
        utilities.assert_equals( expect=main.TRUE, actual=topoResult,
                                 onpass="Topology Check Test successful",
                                 onfail="Topology Check Test NOT successful" )
        main.step( "Checking ONOS nodes" )
        nodeResults = utilities.retry( main.HA.nodesCheck,
                                       False,
                                       args=[main.activeNodes],
                                       attempts=5 )

        utilities.assert_equals( expect=True, actual=nodeResults,
                                 onpass="Nodes check successful",
                                 onfail="Nodes check NOT successful" )
        if not nodeResults:
            for i in main.activeNodes:
                main.log.debug( "{} components not ACTIVE: \n{}".format(
                    main.CLIs[i].name,
                    main.CLIs[i].sendline( "scr:list | grep -v ACTIVE" ) ) )

    def CASE9( self, main ):
        """
        Link s3-s28 down
        """
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        # NOTE: You should probably run a topology check after this

        linkSleep = float( main.params[ 'timers' ][ 'LinkDiscovery' ] )

        description = "Turn off a link to ensure that Link Discovery " +\
                      "is working properly"
        main.case( description )

        main.step( "Kill Link between s3 and s28" )
        LinkDown = main.Mininet1.link( END1="s3", END2="s28", OPTION="down" )
        main.log.info( "Waiting " + str( linkSleep ) +
                       " seconds for link down to be discovered" )
        time.sleep( linkSleep )
        utilities.assert_equals( expect=main.TRUE, actual=LinkDown,
                                 onpass="Link down successful",
                                 onfail="Failed to bring link down" )
        # TODO do some sort of check here

    def CASE10( self, main ):
        """
        Link s3-s28 up
        """
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        # NOTE: You should probably run a topology check after this

        linkSleep = float( main.params[ 'timers' ][ 'LinkDiscovery' ] )

        description = "Restore a link to ensure that Link Discovery is " + \
                      "working properly"
        main.case( description )

        main.step( "Bring link between s3 and s28 back up" )
        LinkUp = main.Mininet1.link( END1="s3", END2="s28", OPTION="up" )
        main.log.info( "Waiting " + str( linkSleep ) +
                       " seconds for link up to be discovered" )
        time.sleep( linkSleep )
        utilities.assert_equals( expect=main.TRUE, actual=LinkUp,
                                 onpass="Link up successful",
                                 onfail="Failed to bring link up" )
        # TODO do some sort of check here

    def CASE11( self, main ):
        """
        Switch Down
        """
        # NOTE: You should probably run a topology check after this
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"

        switchSleep = float( main.params[ 'timers' ][ 'SwitchDiscovery' ] )

        description = "Killing a switch to ensure it is discovered correctly"
        onosCli = main.CLIs[ main.activeNodes[0] ]
        main.case( description )
        switch = main.params[ 'kill' ][ 'switch' ]
        switchDPID = main.params[ 'kill' ][ 'dpid' ]

        # TODO: Make this switch parameterizable
        main.step( "Kill " + switch )
        main.log.info( "Deleting " + switch )
        main.Mininet1.delSwitch( switch )
        main.log.info( "Waiting " + str( switchSleep ) +
                       " seconds for switch down to be discovered" )
        time.sleep( switchSleep )
        device = onosCli.getDevice( dpid=switchDPID )
        # Peek at the deleted switch
        main.log.warn( str( device ) )
        result = main.FALSE
        if device and device[ 'available' ] is False:
            result = main.TRUE
        utilities.assert_equals( expect=main.TRUE, actual=result,
                                 onpass="Kill switch successful",
                                 onfail="Failed to kill switch?" )

    def CASE12( self, main ):
        """
        Switch Up
        """
        # NOTE: You should probably run a topology check after this
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"

        switchSleep = float( main.params[ 'timers' ][ 'SwitchDiscovery' ] )
        switch = main.params[ 'kill' ][ 'switch' ]
        switchDPID = main.params[ 'kill' ][ 'dpid' ]
        links = main.params[ 'kill' ][ 'links' ].split()
        onosCli = main.CLIs[ main.activeNodes[0] ]
        description = "Adding a switch to ensure it is discovered correctly"
        main.case( description )

        main.step( "Add back " + switch )
        main.Mininet1.addSwitch( switch, dpid=switchDPID )
        for peer in links:
            main.Mininet1.addLink( switch, peer )
        ipList = [ node.ip_address for node in main.nodes ]
        main.Mininet1.assignSwController( sw=switch, ip=ipList )
        main.log.info( "Waiting " + str( switchSleep ) +
                       " seconds for switch up to be discovered" )
        time.sleep( switchSleep )
        device = onosCli.getDevice( dpid=switchDPID )
        # Peek at the deleted switch
        main.log.warn( str( device ) )
        result = main.FALSE
        if device and device[ 'available' ]:
            result = main.TRUE
        utilities.assert_equals( expect=main.TRUE, actual=result,
                                 onpass="add switch successful",
                                 onfail="Failed to add switch?" )

    def CASE13( self, main ):
        """
        Clean up
        """
        import os
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        # printing colors to terminal
        colors = { 'cyan': '\033[96m', 'purple': '\033[95m',
                   'blue': '\033[94m', 'green': '\033[92m',
                   'yellow': '\033[93m', 'red': '\033[91m', 'end': '\033[0m' }
        main.case( "Test Cleanup" )
        main.step( "Killing tcpdumps" )
        main.Mininet2.stopTcpdump()

        testname = main.TEST
        if main.params[ 'BACKUP' ][ 'ENABLED' ] == "True":
            main.step( "Copying MN pcap and ONOS log files to test station" )
            teststationUser = main.params[ 'BACKUP' ][ 'TESTONUSER' ]
            teststationIP = main.params[ 'BACKUP' ][ 'TESTONIP' ]
            # NOTE: MN Pcap file is being saved to logdir.
            #       We scp this file as MN and TestON aren't necessarily the same vm

            # FIXME: To be replaced with a Jenkin's post script
            # TODO: Load these from params
            # NOTE: must end in /
            logFolder = "/opt/onos/log/"
            logFiles = [ "karaf.log", "karaf.log.1" ]
            # NOTE: must end in /
            for f in logFiles:
                for node in main.nodes:
                    dstName = main.logdir + "/" + node.name + "-" + f
                    main.ONOSbench.secureCopy( node.user_name, node.ip_address,
                                               logFolder + f, dstName )
            # std*.log's
            # NOTE: must end in /
            logFolder = "/opt/onos/var/"
            logFiles = [ "stderr.log", "stdout.log" ]
            # NOTE: must end in /
            for f in logFiles:
                for node in main.nodes:
                    dstName = main.logdir + "/" + node.name + "-" + f
                    main.ONOSbench.secureCopy( node.user_name, node.ip_address,
                                               logFolder + f, dstName )
        else:
            main.log.debug( "skipping saving log files" )

        main.step( "Stopping Mininet" )
        mnResult = main.Mininet1.stopNet()
        utilities.assert_equals( expect=main.TRUE, actual=mnResult,
                                 onpass="Mininet stopped",
                                 onfail="MN cleanup NOT successful" )

        main.step( "Checking ONOS Logs for errors" )
        for node in main.nodes:
            main.log.debug( "Checking logs for errors on " + node.name + ":" )
            main.log.warn( main.ONOSbench.checkLogs( node.ip_address ) )

        try:
            timerLog = open( main.logdir + "/Timers.csv", 'w')
            # Overwrite with empty line and close
            labels = "Gossip Intents, Restart"
            data = str( gossipTime ) + ", " + str( main.restartTime )
            timerLog.write( labels + "\n" + data )
            timerLog.close()
        except NameError, e:
            main.log.exception(e)

    def CASE14( self, main ):
        """
        start election app on all onos nodes
        """
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"

        main.case("Start Leadership Election app")
        main.step( "Install leadership election app" )
        onosCli = main.CLIs[ main.activeNodes[0] ]
        appResult = onosCli.activateApp( "org.onosproject.election" )
        utilities.assert_equals(
            expect=main.TRUE,
            actual=appResult,
            onpass="Election app installed",
            onfail="Something went wrong with installing Leadership election" )

        main.step( "Run for election on each node" )
        for i in main.activeNodes:
            main.CLIs[i].electionTestRun()
        time.sleep(5)
        activeCLIs = [ main.CLIs[i] for i in main.activeNodes ]
        sameResult, leaders = main.HA.consistentLeaderboards( activeCLIs )
        utilities.assert_equals(
            expect=True,
            actual=sameResult,
            onpass="All nodes see the same leaderboards",
            onfail="Inconsistent leaderboards" )

        if sameResult:
            leader = leaders[ 0 ][ 0 ]
            if main.nodes[main.activeNodes[0]].ip_address in leader:
                correctLeader = True
            else:
                correctLeader = False
            main.step( "First node was elected leader" )
            utilities.assert_equals(
                expect=True,
                actual=correctLeader,
                onpass="Correct leader was elected",
                onfail="Incorrect leader" )

    def CASE15( self, main ):
        """
        Check that Leadership Election is still functional
            15.1 Run election on each node
            15.2 Check that each node has the same leaders and candidates
            15.3 Find current leader and withdraw
            15.4 Check that a new node was elected leader
            15.5 Check that that new leader was the candidate of old leader
            15.6 Run for election on old leader
            15.7 Check that oldLeader is a candidate, and leader if only 1 node
            15.8 Make sure that the old leader was added to the candidate list

            old and new variable prefixes refer to data from before vs after
                withdrawl and later before withdrawl vs after re-election
        """
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        assert main.CLIs, "main.CLIs not defined"
        assert main.nodes, "main.nodes not defined"

        description = "Check that Leadership Election is still functional"
        main.case( description )
        # NOTE: Need to re-run after restarts since being a canidate is not persistant

        oldLeaders = []  # list of lists of each nodes' candidates before
        newLeaders = []  # list of lists of each nodes' candidates after
        oldLeader = ''  # the old leader from oldLeaders, None if not same
        newLeader = ''  # the new leaders fron newLoeaders, None if not same
        oldLeaderCLI = None  # the CLI of the old leader used for re-electing
        expectNoLeader = False  # True when there is only one leader
        if main.numCtrls == 1:
            expectNoLeader = True

        main.step( "Run for election on each node" )
        electionResult = main.TRUE

        for i in main.activeNodes:  # run test election on each node
            if main.CLIs[i].electionTestRun() == main.FALSE:
                electionResult = main.FALSE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=electionResult,
            onpass="All nodes successfully ran for leadership",
            onfail="At least one node failed to run for leadership" )

        if electionResult == main.FALSE:
            main.log.error(
                "Skipping Test Case because Election Test App isn't loaded" )
            main.skipCase()

        main.step( "Check that each node shows the same leader and candidates" )
        failMessage = "Nodes have different leaderboards"
        activeCLIs = [ main.CLIs[i] for i in main.activeNodes ]
        sameResult, oldLeaders = main.HA.consistentLeaderboards( activeCLIs )
        if sameResult:
            oldLeader = oldLeaders[ 0 ][ 0 ]
            main.log.warn( oldLeader )
        else:
            oldLeader = None
        utilities.assert_equals(
            expect=True,
            actual=sameResult,
            onpass="Leaderboards are consistent for the election topic",
            onfail=failMessage )

        main.step( "Find current leader and withdraw" )
        withdrawResult = main.TRUE
        # do some sanity checking on leader before using it
        if oldLeader is None:
            main.log.error( "Leadership isn't consistent." )
            withdrawResult = main.FALSE
        # Get the CLI of the oldLeader
        for i in main.activeNodes:
            if oldLeader == main.nodes[ i ].ip_address:
                oldLeaderCLI = main.CLIs[ i ]
                break
        else:  # FOR/ELSE statement
            main.log.error( "Leader election, could not find current leader" )
        if oldLeader:
            withdrawResult = oldLeaderCLI.electionTestWithdraw()
        utilities.assert_equals(
            expect=main.TRUE,
            actual=withdrawResult,
            onpass="Node was withdrawn from election",
            onfail="Node was not withdrawn from election" )

        main.step( "Check that a new node was elected leader" )
        failMessage = "Nodes have different leaders"
        # Get new leaders and candidates
        newLeaderResult, newLeaders = main.HA.consistentLeaderboards( activeCLIs )
        newLeader = None
        if newLeaderResult:
            if newLeaders[ 0 ][ 0 ] == 'none':
                main.log.error( "No leader was elected on at least 1 node" )
                if not expectNoLeader:
                    newLeaderResult = False
            newLeader = newLeaders[ 0 ][ 0 ]

        # Check that the new leader is not the older leader, which was withdrawn
        if newLeader == oldLeader:
            newLeaderResult = False
            main.log.error( "All nodes still see old leader: " + str( oldLeader ) +
                " as the current leader" )
        utilities.assert_equals(
            expect=True,
            actual=newLeaderResult,
            onpass="Leadership election passed",
            onfail="Something went wrong with Leadership election" )

        main.step( "Check that that new leader was the candidate of old leader" )
        # candidates[ 2 ] should become the top candidate after withdrawl
        correctCandidateResult = main.TRUE
        if expectNoLeader:
            if newLeader == 'none':
                main.log.info( "No leader expected. None found. Pass" )
                correctCandidateResult = main.TRUE
            else:
                main.log.info( "Expected no leader, got: " + str( newLeader ) )
                correctCandidateResult = main.FALSE
        elif len( oldLeaders[0] ) >= 3:
            if newLeader == oldLeaders[ 0 ][ 2 ]:
                # correct leader was elected
                correctCandidateResult = main.TRUE
            else:
                correctCandidateResult = main.FALSE
                main.log.error( "Candidate {} was elected. {} should have had priority.".format(
                                    newLeader, oldLeaders[ 0 ][ 2 ] ) )
        else:
            main.log.warn( "Could not determine who should be the correct leader" )
            main.log.debug( oldLeaders[ 0 ] )
            correctCandidateResult = main.FALSE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=correctCandidateResult,
            onpass="Correct Candidate Elected",
            onfail="Incorrect Candidate Elected" )

        main.step( "Run for election on old leader( just so everyone " +
                   "is in the hat )" )
        if oldLeaderCLI is not None:
            runResult = oldLeaderCLI.electionTestRun()
        else:
            main.log.error( "No old leader to re-elect" )
            runResult = main.FALSE
        utilities.assert_equals(
            expect=main.TRUE,
            actual=runResult,
            onpass="App re-ran for election",
            onfail="App failed to run for election" )

        main.step(
            "Check that oldLeader is a candidate, and leader if only 1 node" )
        # verify leader didn't just change
        # Get new leaders and candidates
        reRunLeaders = []
        time.sleep( 5 ) # Paremterize
        positionResult, reRunLeaders = main.HA.consistentLeaderboards( activeCLIs )

        # Check that the re-elected node is last on the candidate List
        if not reRunLeaders[0]:
            positionResult = main.FALSE
        elif oldLeader != reRunLeaders[ 0 ][ -1 ]:
            main.log.error( "Old Leader ({}) not in the proper position: {} ".format( str( oldLeader),
                                                                                      str( reRunLeaders[ 0 ] ) ) )
            positionResult = main.FALSE
        utilities.assert_equals(
            expect=True,
            actual=positionResult,
            onpass="Old leader successfully re-ran for election",
            onfail="Something went wrong with Leadership election after " +
                   "the old leader re-ran for election" )

    def CASE16( self, main ):
        """
        Install Distributed Primitives app
        """
        import time
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        assert main.CLIs, "main.CLIs not defined"
        assert main.nodes, "main.nodes not defined"

        # Variables for the distributed primitives tests
        global pCounterName
        global pCounterValue
        global onosSet
        global onosSetName
        pCounterName = "TestON-Partitions"
        pCounterValue = 0
        onosSet = set([])
        onosSetName = "TestON-set"

        description = "Install Primitives app"
        main.case( description )
        main.step( "Install Primitives app" )
        appName = "org.onosproject.distributedprimitives"
        node = main.activeNodes[0]
        appResults = main.CLIs[node].activateApp( appName )
        utilities.assert_equals( expect=main.TRUE,
                                 actual=appResults,
                                 onpass="Primitives app activated",
                                 onfail="Primitives app not activated" )
        time.sleep( 5 )  # To allow all nodes to activate

    def CASE17( self, main ):
        """
        Check for basic functionality with distributed primitives
        """
        # Make sure variables are defined/set
        assert main.numCtrls, "main.numCtrls not defined"
        assert main, "main not defined"
        assert utilities.assert_equals, "utilities.assert_equals not defined"
        assert main.CLIs, "main.CLIs not defined"
        assert main.nodes, "main.nodes not defined"
        assert pCounterName, "pCounterName not defined"
        assert onosSetName, "onosSetName not defined"
        # NOTE: assert fails if value is 0/None/Empty/False
        try:
            pCounterValue
        except NameError:
            main.log.error( "pCounterValue not defined, setting to 0" )
            pCounterValue = 0
        try:
            onosSet
        except NameError:
            main.log.error( "onosSet not defined, setting to empty Set" )
            onosSet = set([])
        # Variables for the distributed primitives tests. These are local only
        addValue = "a"
        addAllValue = "a b c d e f"
        retainValue = "c d e f"

        description = "Check for basic functionality with distributed " +\
                      "primitives"
        main.case( description )
        main.caseExplanation = "Test the methods of the distributed " +\
                                "primitives (counters and sets) throught the cli"
        # DISTRIBUTED ATOMIC COUNTERS
        # Partitioned counters
        main.step( "Increment then get a default counter on each node" )
        pCounters = []
        threads = []
        addedPValues = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].counterTestAddAndGet,
                             name="counterAddAndGet-" + str( i ),
                             args=[ pCounterName ] )
            pCounterValue += 1
            addedPValues.append( pCounterValue )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            pCounters.append( t.result )
        # Check that counter incremented numController times
        pCounterResults = True
        for i in addedPValues:
            tmpResult = i in pCounters
            pCounterResults = pCounterResults and tmpResult
            if not tmpResult:
                main.log.error( str( i ) + " is not in partitioned "
                                "counter incremented results" )
        utilities.assert_equals( expect=True,
                                 actual=pCounterResults,
                                 onpass="Default counter incremented",
                                 onfail="Error incrementing default" +
                                        " counter" )

        main.step( "Get then Increment a default counter on each node" )
        pCounters = []
        threads = []
        addedPValues = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].counterTestGetAndAdd,
                             name="counterGetAndAdd-" + str( i ),
                             args=[ pCounterName ] )
            addedPValues.append( pCounterValue )
            pCounterValue += 1
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            pCounters.append( t.result )
        # Check that counter incremented numController times
        pCounterResults = True
        for i in addedPValues:
            tmpResult = i in pCounters
            pCounterResults = pCounterResults and tmpResult
            if not tmpResult:
                main.log.error( str( i ) + " is not in partitioned "
                                "counter incremented results" )
        utilities.assert_equals( expect=True,
                                 actual=pCounterResults,
                                 onpass="Default counter incremented",
                                 onfail="Error incrementing default" +
                                        " counter" )

        main.step( "Counters we added have the correct values" )
        incrementCheck = main.HA.counterCheck( pCounterName, pCounterValue )
        utilities.assert_equals( expect=main.TRUE,
                                 actual=incrementCheck,
                                 onpass="Added counters are correct",
                                 onfail="Added counters are incorrect" )

        main.step( "Add -8 to then get a default counter on each node" )
        pCounters = []
        threads = []
        addedPValues = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].counterTestAddAndGet,
                             name="counterIncrement-" + str( i ),
                             args=[ pCounterName ],
                             kwargs={ "delta": -8 } )
            pCounterValue += -8
            addedPValues.append( pCounterValue )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            pCounters.append( t.result )
        # Check that counter incremented numController times
        pCounterResults = True
        for i in addedPValues:
            tmpResult = i in pCounters
            pCounterResults = pCounterResults and tmpResult
            if not tmpResult:
                main.log.error( str( i ) + " is not in partitioned "
                                "counter incremented results" )
        utilities.assert_equals( expect=True,
                                 actual=pCounterResults,
                                 onpass="Default counter incremented",
                                 onfail="Error incrementing default" +
                                        " counter" )

        main.step( "Add 5 to then get a default counter on each node" )
        pCounters = []
        threads = []
        addedPValues = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].counterTestAddAndGet,
                             name="counterIncrement-" + str( i ),
                             args=[ pCounterName ],
                             kwargs={ "delta": 5 } )
            pCounterValue += 5
            addedPValues.append( pCounterValue )
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            pCounters.append( t.result )
        # Check that counter incremented numController times
        pCounterResults = True
        for i in addedPValues:
            tmpResult = i in pCounters
            pCounterResults = pCounterResults and tmpResult
            if not tmpResult:
                main.log.error( str( i ) + " is not in partitioned "
                                "counter incremented results" )
        utilities.assert_equals( expect=True,
                                 actual=pCounterResults,
                                 onpass="Default counter incremented",
                                 onfail="Error incrementing default" +
                                        " counter" )

        main.step( "Get then add 5 to a default counter on each node" )
        pCounters = []
        threads = []
        addedPValues = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].counterTestGetAndAdd,
                             name="counterIncrement-" + str( i ),
                             args=[ pCounterName ],
                             kwargs={ "delta": 5 } )
            addedPValues.append( pCounterValue )
            pCounterValue += 5
            threads.append( t )
            t.start()

        for t in threads:
            t.join()
            pCounters.append( t.result )
        # Check that counter incremented numController times
        pCounterResults = True
        for i in addedPValues:
            tmpResult = i in pCounters
            pCounterResults = pCounterResults and tmpResult
            if not tmpResult:
                main.log.error( str( i ) + " is not in partitioned "
                                "counter incremented results" )
        utilities.assert_equals( expect=True,
                                 actual=pCounterResults,
                                 onpass="Default counter incremented",
                                 onfail="Error incrementing default" +
                                        " counter" )

        main.step( "Counters we added have the correct values" )
        incrementCheck = main.HA.counterCheck( pCounterName, pCounterValue )
        utilities.assert_equals( expect=main.TRUE,
                                 actual=incrementCheck,
                                 onpass="Added counters are correct",
                                 onfail="Added counters are incorrect" )

        # DISTRIBUTED SETS
        main.step( "Distributed Set get" )
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )

        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        utilities.assert_equals( expect=main.TRUE,
                                 actual=getResults,
                                 onpass="Set elements are correct",
                                 onfail="Set elements are incorrect" )

        main.step( "Distributed Set size" )
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )

        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        utilities.assert_equals( expect=main.TRUE,
                                 actual=sizeResults,
                                 onpass="Set sizes are correct",
                                 onfail="Set sizes are incorrect" )

        main.step( "Distributed Set add()" )
        onosSet.add( addValue )
        addResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestAdd,
                             name="setTestAdd-" + str( i ),
                             args=[ onosSetName, addValue ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            addResponses.append( t.result )

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        addResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if addResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif addResponses[ i ] == main.FALSE:
                # Already in set, probably fine
                pass
            elif addResponses[ i ] == main.ERROR:
                # Error in execution
                addResults = main.FALSE
            else:
                # unexpected result
                addResults = main.FALSE
        if addResults != main.TRUE:
            main.log.error( "Error executing set add" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node + " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node + " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        addResults = addResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=addResults,
                                 onpass="Set add correct",
                                 onfail="Set add was incorrect" )

        main.step( "Distributed Set addAll()" )
        onosSet.update( addAllValue.split() )
        addResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestAdd,
                             name="setTestAddAll-" + str( i ),
                             args=[ onosSetName, addAllValue ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            addResponses.append( t.result )

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        addAllResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if addResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif addResponses[ i ] == main.FALSE:
                # Already in set, probably fine
                pass
            elif addResponses[ i ] == main.ERROR:
                # Error in execution
                addAllResults = main.FALSE
            else:
                # unexpected result
                addAllResults = main.FALSE
        if addAllResults != main.TRUE:
            main.log.error( "Error executing set addAll" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        addAllResults = addAllResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=addAllResults,
                                 onpass="Set addAll correct",
                                 onfail="Set addAll was incorrect" )

        main.step( "Distributed Set contains()" )
        containsResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setContains-" + str( i ),
                             args=[ onosSetName ],
                             kwargs={ "values": addValue } )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            # NOTE: This is the tuple
            containsResponses.append( t.result )

        containsResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if containsResponses[ i ] == main.ERROR:
                containsResults = main.FALSE
            else:
                containsResults = containsResults and\
                                  containsResponses[ i ][ 1 ]
        utilities.assert_equals( expect=main.TRUE,
                                 actual=containsResults,
                                 onpass="Set contains is functional",
                                 onfail="Set contains failed" )

        main.step( "Distributed Set containsAll()" )
        containsAllResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setContainsAll-" + str( i ),
                             args=[ onosSetName ],
                             kwargs={ "values": addAllValue } )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            # NOTE: This is the tuple
            containsAllResponses.append( t.result )

        containsAllResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if containsResponses[ i ] == main.ERROR:
                containsResults = main.FALSE
            else:
                containsResults = containsResults and\
                                  containsResponses[ i ][ 1 ]
        utilities.assert_equals( expect=main.TRUE,
                                 actual=containsAllResults,
                                 onpass="Set containsAll is functional",
                                 onfail="Set containsAll failed" )

        main.step( "Distributed Set remove()" )
        onosSet.remove( addValue )
        removeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestRemove,
                             name="setTestRemove-" + str( i ),
                             args=[ onosSetName, addValue ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            removeResponses.append( t.result )

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        removeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if removeResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif removeResponses[ i ] == main.FALSE:
                # not in set, probably fine
                pass
            elif removeResponses[ i ] == main.ERROR:
                # Error in execution
                removeResults = main.FALSE
            else:
                # unexpected result
                removeResults = main.FALSE
        if removeResults != main.TRUE:
            main.log.error( "Error executing set remove" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        removeResults = removeResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=removeResults,
                                 onpass="Set remove correct",
                                 onfail="Set remove was incorrect" )

        main.step( "Distributed Set removeAll()" )
        onosSet.difference_update( addAllValue.split() )
        removeAllResponses = []
        threads = []
        try:
            for i in main.activeNodes:
                t = main.Thread( target=main.CLIs[i].setTestRemove,
                                 name="setTestRemoveAll-" + str( i ),
                                 args=[ onosSetName, addAllValue ] )
                threads.append( t )
                t.start()
            for t in threads:
                t.join()
                removeAllResponses.append( t.result )
        except Exception, e:
            main.log.exception(e)

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        removeAllResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if removeAllResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif removeAllResponses[ i ] == main.FALSE:
                # not in set, probably fine
                pass
            elif removeAllResponses[ i ] == main.ERROR:
                # Error in execution
                removeAllResults = main.FALSE
            else:
                # unexpected result
                removeAllResults = main.FALSE
        if removeAllResults != main.TRUE:
            main.log.error( "Error executing set removeAll" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        removeAllResults = removeAllResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=removeAllResults,
                                 onpass="Set removeAll correct",
                                 onfail="Set removeAll was incorrect" )

        main.step( "Distributed Set addAll()" )
        onosSet.update( addAllValue.split() )
        addResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestAdd,
                             name="setTestAddAll-" + str( i ),
                             args=[ onosSetName, addAllValue ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            addResponses.append( t.result )

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        addAllResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if addResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif addResponses[ i ] == main.FALSE:
                # Already in set, probably fine
                pass
            elif addResponses[ i ] == main.ERROR:
                # Error in execution
                addAllResults = main.FALSE
            else:
                # unexpected result
                addAllResults = main.FALSE
        if addAllResults != main.TRUE:
            main.log.error( "Error executing set addAll" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        addAllResults = addAllResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=addAllResults,
                                 onpass="Set addAll correct",
                                 onfail="Set addAll was incorrect" )

        main.step( "Distributed Set clear()" )
        onosSet.clear()
        clearResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestRemove,
                             name="setTestClear-" + str( i ),
                             args=[ onosSetName, " "],  # Values doesn't matter
                             kwargs={ "clear": True } )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            clearResponses.append( t.result )

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        clearResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if clearResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif clearResponses[ i ] == main.FALSE:
                # Nothing set, probably fine
                pass
            elif clearResponses[ i ] == main.ERROR:
                # Error in execution
                clearResults = main.FALSE
            else:
                # unexpected result
                clearResults = main.FALSE
        if clearResults != main.TRUE:
            main.log.error( "Error executing set clear" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        clearResults = clearResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=clearResults,
                                 onpass="Set clear correct",
                                 onfail="Set clear was incorrect" )

        main.step( "Distributed Set addAll()" )
        onosSet.update( addAllValue.split() )
        addResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestAdd,
                             name="setTestAddAll-" + str( i ),
                             args=[ onosSetName, addAllValue ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            addResponses.append( t.result )

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        addAllResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if addResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif addResponses[ i ] == main.FALSE:
                # Already in set, probably fine
                pass
            elif addResponses[ i ] == main.ERROR:
                # Error in execution
                addAllResults = main.FALSE
            else:
                # unexpected result
                addAllResults = main.FALSE
        if addAllResults != main.TRUE:
            main.log.error( "Error executing set addAll" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node +
                                " expected a size of " + str( size ) +
                                " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        addAllResults = addAllResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=addAllResults,
                                 onpass="Set addAll correct",
                                 onfail="Set addAll was incorrect" )

        main.step( "Distributed Set retain()" )
        onosSet.intersection_update( retainValue.split() )
        retainResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestRemove,
                             name="setTestRetain-" + str( i ),
                             args=[ onosSetName, retainValue ],
                             kwargs={ "retain": True } )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            retainResponses.append( t.result )

        # main.TRUE = successfully changed the set
        # main.FALSE = action resulted in no change in set
        # main.ERROR - Some error in executing the function
        retainResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            if retainResponses[ i ] == main.TRUE:
                # All is well
                pass
            elif retainResponses[ i ] == main.FALSE:
                # Already in set, probably fine
                pass
            elif retainResponses[ i ] == main.ERROR:
                # Error in execution
                retainResults = main.FALSE
            else:
                # unexpected result
                retainResults = main.FALSE
        if retainResults != main.TRUE:
            main.log.error( "Error executing set retain" )

        # Check if set is still correct
        size = len( onosSet )
        getResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestGet,
                             name="setTestGet-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            getResponses.append( t.result )
        getResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if isinstance( getResponses[ i ], list):
                current = set( getResponses[ i ] )
                if len( current ) == len( getResponses[ i ] ):
                    # no repeats
                    if onosSet != current:
                        main.log.error( "ONOS" + node +
                                        " has incorrect view" +
                                        " of set " + onosSetName + ":\n" +
                                        str( getResponses[ i ] ) )
                        main.log.debug( "Expected: " + str( onosSet ) )
                        main.log.debug( "Actual: " + str( current ) )
                        getResults = main.FALSE
                else:
                    # error, set is not a set
                    main.log.error( "ONOS" + node +
                                    " has repeat elements in" +
                                    " set " + onosSetName + ":\n" +
                                    str( getResponses[ i ] ) )
                    getResults = main.FALSE
            elif getResponses[ i ] == main.ERROR:
                getResults = main.FALSE
        sizeResponses = []
        threads = []
        for i in main.activeNodes:
            t = main.Thread( target=main.CLIs[i].setTestSize,
                             name="setTestSize-" + str( i ),
                             args=[ onosSetName ] )
            threads.append( t )
            t.start()
        for t in threads:
            t.join()
            sizeResponses.append( t.result )
        sizeResults = main.TRUE
        for i in range( len( main.activeNodes ) ):
            node = str( main.activeNodes[i] + 1 )
            if size != sizeResponses[ i ]:
                sizeResults = main.FALSE
                main.log.error( "ONOS" + node + " expected a size of " +
                                str( size ) + " for set " + onosSetName +
                                " but got " + str( sizeResponses[ i ] ) )
        retainResults = retainResults and getResults and sizeResults
        utilities.assert_equals( expect=main.TRUE,
                                 actual=retainResults,
                                 onpass="Set retain correct",
                                 onfail="Set retain was incorrect" )

        # Transactional maps
        main.step( "Partitioned Transactional maps put" )
        tMapValue = "Testing"
        numKeys = 100
        putResult = True
        node = main.activeNodes[0]
        putResponses = main.CLIs[node].transactionalMapPut( numKeys, tMapValue )
        if putResponses and len( putResponses ) == 100:
            for i in putResponses:
                if putResponses[ i ][ 'value' ] != tMapValue:
                    putResult = False
        else:
            putResult = False
        if not putResult:
            main.log.debug( "Put response values: " + str( putResponses ) )
        utilities.assert_equals( expect=True,
                                 actual=putResult,
                                 onpass="Partitioned Transactional Map put successful",
                                 onfail="Partitioned Transactional Map put values are incorrect" )

        main.step( "Partitioned Transactional maps get" )
        # FIXME: is this sleep needed?
        time.sleep( 5 )

        getCheck = True
        for n in range( 1, numKeys + 1 ):
            getResponses = []
            threads = []
            valueCheck = True
            for i in main.activeNodes:
                t = main.Thread( target=main.CLIs[i].transactionalMapGet,
                                 name="TMap-get-" + str( i ),
                                 args=[ "Key" + str( n ) ] )
                threads.append( t )
                t.start()
            for t in threads:
                t.join()
                getResponses.append( t.result )
            for node in getResponses:
                if node != tMapValue:
                    valueCheck = False
            if not valueCheck:
                main.log.warn( "Values for key 'Key" + str( n ) + "' do not match:" )
                main.log.warn( getResponses )
            getCheck = getCheck and valueCheck
        utilities.assert_equals( expect=True,
                                 actual=getCheck,
                                 onpass="Partitioned Transactional Map get values were correct",
                                 onfail="Partitioned Transactional Map values incorrect" )
