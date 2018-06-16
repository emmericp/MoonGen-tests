import unittest
import subprocess
import utility
import time
import sys
import os.path
from datetime import datetime
from FrameworkSubprocess import SubHandler


class BindDevices(unittest.TestCase):
    # devicelist = list()
    logdir = 'logs/'
    logname = 'defaultLog'
    casename = 'default case name'
    testlog = None
    summarylog = None

    # testlog = open(logname, 'w') # this has to be overridden by subclass

    def __init__(self, devicelist, path):
        super(BindDevices, self).__init__()
        self.devicelist = devicelist
        self.path = path

    def setUp(self):  # set the devices
        utility.binddevices(self.devicelist)
        self.initTestlog()

    def tearDown(self):
        utility.unbinddevices(self.devicelist)
        self.testlog.close()
        self.summarylog.write('\n=== END OF SUMMARY ===\n')
        self.summarylog.close()

    def initTestlog(self):
        # check if, in the log dir, a dir with this date is available
        now = datetime.now()
        datesuffix = str(now.year) + '-' + str(now.month) + '-' + str(now.day)
        self.logdir += datesuffix + '/'
        if not os.path.isdir(self.logdir):
            os.mkdir('logs/' + datesuffix)
        self.logname = self.logdir + self.logname
        self.logname += '_' + str(now.hour) + ':' + str(now.minute) + ':' + str(now.second)

        # obselete
        # if os.path.isfile(self.logname):
        #     i = 2
        #     while os.path.isfile(self.logname + str(i)):
        #         i += 1
        #     self.logname += str(i)
        self.testlog = open(self.logname, 'w')
        # open a summary log
        self.summarylog = open(self.logname + '_summary', 'w')
        self.summarylog.write('=== SUMMARY ===\n\n')

    def writetoread(self):
        self.testlog.close()
        self.testlog = open(self.logname, 'r')


class TerminatingTest(BindDevices):
    duration = 20
    pollrate = 2
    casename = 'default terminating / simple case name'
    termtimelimit = 2  # was 4
    termloopdelta = 0.5
    resulttolorance = 0.9  # type: float
    testlog = None

    def terminate(self, process):
        timecounter = 0
        while timecounter < self.duration:
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(self.pollrate)
            timecounter += self.pollrate
        print''
        process.terminate()
        # check if process terminated, if not report a bug
        print'Waiting for termination'
        # time.sleep(20)  # trying a delay before the poll
        timecounter = 0
        while process.poll() is None or timecounter <= self.termtimelimit:
            time.sleep(self.termloopdelta)
            timecounter += self.termloopdelta
            sys.stdout.write('.')
            sys.stdout.flush()
        print''
        print('Time it took to terminate: %d sec' % timecounter)
        # if process.poll() is None:
        if process.returncode is None:
            process.kill()
            print'Process not terminated!--'

    def runTest(self):
        print("=====Testing MoonGen Case: %s, this will take %d seconds" % (self.casename, int(self.duration)))
        p = self.executetest()
        # p.wait()
        # print 'udp simple test launched, terminates in 20 seconds'
        # time.sleep(20)
        # p.terminate()
        self.terminate(p)
        self.writetoread()
        print('terminated, closed test log')
        # sucess yet to be specified
        self.checkresult()

    def executetest(self):
        return subprocess.Popen()

    valueindex = {'txmax': 0,
                  'rxmax': 1,
                  'txavg': 2,
                  'rxavg': 3,
                  'txmin': 4,
                  'rxmin': 5}

    def adjustvalues(self, vallist, txvalue, rxvalue, firstrun):
        if txvalue > vallist[self.valueindex['txmax']]:
            vallist[self.valueindex['txmax']] = txvalue
            if firstrun is True:
                vallist[self.valueindex['txmin']] = vallist[self.valueindex['txmax']]
        if txvalue < vallist[self.valueindex['txmin']]:
            vallist[self.valueindex['txmin']] = txvalue
        if rxvalue > vallist[self.valueindex['rxmax']]:
            vallist[self.valueindex['rxmax']] = rxvalue
            if firstrun is True:
                vallist[self.valueindex['rxmin']] = vallist[self.valueindex['rxmax']]
        if rxvalue < vallist[self.valueindex['rxmin']]:
            vallist[self.valueindex['rxmin']] = rxvalue

        vallist[self.valueindex['txavg']] += txvalue
        vallist[self.valueindex['rxavg']] += rxvalue

        return vallist

    def initvalues(self):
        # list stores interesting values, to be printed
        # 0     1       2      3      4      5
        txmax, rxmax, txavg, rxavg, txmin, rxmin = (0.0,) * 6
        reslist = [txmax, rxmax, txavg, rxavg, txmin, rxmin]
        return reslist

    def checkalerts(self, lines, index):
        if '[FATAL]' in lines[index] or '[ERROR]' in lines[index] or '[WARN]' in lines[index]:
            print'--line of interest: ' + lines[index]
            self.summarylog.write('line of interest: ' + lines[index] + '\n')
        elif 'Saving histogram to' in lines[index]:
            for i in range(index, len(lines)):
                self.summarylog.write(lines[i])
            return False
        return True

    def extractvalues(self, lines, index):
        return list()

    def evaluate(self, lines, index):
        result = True
        # tx / rx values
        # txmax, rxmax, txavg, rxavg, txmin, rxmin = (0.0,) * 6
        vallist = self.initvalues()
        avgcounter = 0
        firstvalueskip = True
        firstminmax = True
        # method parses relevant data from the log file
        for i in range(index, len(lines)):
            if not result:
                break
            # if '[FATAL]' in lines[i] or '[ERROR]' in lines[i] or '[WARN]' in lines[i]:
            #     print'--line of interest: ' + lines[i]
            #     self.summarylog.write('line of interest: ' + lines[i] + '\n')
            # elif 'Saving histogram to' in lines[i]:
            #     for j in range(i, len(lines)):
            #         self.summarylog.write(lines[j])
            #     break
            if self.checkalerts(lines, i) is False:
                break
            elif '[Device: id=0]' in lines[i]:
                if firstvalueskip:
                    firstvalueskip = False
                    continue
                # TODO get the tx value
                line1 = lines[i].split()
                for j in range(0, len(line1)):
                    if 'TX' in line1[j]:
                        txvalue = float(line1[j + 1])
                        # TODO here get the rx value
                        if '[Device: id=1]' not in lines[i + 1]:
                            continue
                        line2 = lines[i + 1].split()
                        for k in range(0, len(line2)):
                            if 'RX' in line2[k]:
                                rxvalue = float(line2[k + 1])
                                if self.checkvaluesarezero(txvalue, rxvalue) is True
                                    result = False
                                # adjust values
                                vallist = self.adjustvalues(vallist, txvalue, rxvalue, firstminmax)
                                if firstminmax is True:
                                    firstminmax = False
                                # if txvalue > txmax:
                                #     txmax = txvalue
                                #     if firstminmax:
                                #         txmin = txmax
                                # if txvalue < txmin:
                                #     txmin = txvalue
                                # if rxvalue > rxmax:
                                #     rxmax = rxvalue
                                #     if firstminmax:
                                #         rxmin = rxvalue
                                #         firstminmax = False
                                # if rxvalue < rxmin:
                                #     rxmin = rxvalue
                                # txavg += txvalue
                                # rxavg += rxvalue
                                avgcounter += 1
                                # TODO here check result condition
                                result = result and (rxvalue > txvalue * self.resulttolorance)
                                break
                        break
        # TODO here adjust avarages
        vallist[self.valueindex['txavg']] /= float(avgcounter)  # tx avg
        vallist[self.valueindex['rxavg']] /= float(avgcounter)  # rx avg
        self.summarylog.write('TX / RX Values of this test case')
        # TODO here write reseults to log
        self.summarylog.write(
            'TX values are:\n MAX = ' + str(vallist[self.valueindex['txmax']]) + '\n MIN = ' + str(
                vallist[self.valueindex['txmin']]) + '\n AVG = ' + str(vallist[self.valueindex['txavg']]) + '\n')
        self.summarylog.write(
            'RX values are:\n MAX = ' + str(vallist[self.valueindex['rxmax']]) + '\n MIN = ' + str(
                vallist[self.valueindex['rxmin']]) + '\n AVG = ' + str(vallist[self.valueindex['rxavg']]) + '\n')
        self.summarylog.write(
            'Conclusion: has RX value always been at least ' + str(self.resulttolorance * 100) + ' % of TX? : ' + str(
                result) + '\n')
        self.assertTrue(result,
                        msg='This means that the RX values were not over 90 percent of TX values at all times')

    def checkdevicesfound(self, lines):
        for i in range(0, len(lines)):
            if 'Found 0 usable devices:' in lines[i]:
                msg = 'Found 0 usable devices. Possible reasons: no devices, hugepages'
                self.summarylog.write(msg + '\n')
                self.assertTrue(False, msg=msg)
            elif '2 devices are up' in lines[i]:
                return i
        self.summarylog.write('Devices were not up\n')
        self.assertTrue(False, msg='Devices are not up')

    def checkresult(self):
        lines = self.testlog.readlines()
        index = self.checkdevicesfound(lines)
        self.evaluate(lines, index)

    def checkvaluesarezero(self, value1, value2):
        if value1 == 0.0 and value2 == 0.0:
            msg = 'TX / RX values are 0. Test might not be suited for testd devices'
            self.summarylog.write(msg + '\n')
            self.assertTrue(False, msg=msg)
            return True


class TwoWayTerminatingTest(TerminatingTest):

    def initvalues(self):
        # list stores interesting values, to be printed

        tx1max, tx2max, rx1max, rx2max, tx1avg, tx2avg, rx1avg, rx2avg, tx1min, tx2min, rx1min, rx2min = (0.0,) * 12
        device1 = [tx1max, rx1max, tx1avg, rx1avg, tx1min, rx1min]
        device2 = [tx2max, rx2max, tx2avg, rx2avg, tx2min, rx2min]
        reslist = [device1, device2]
        return reslist

    def parsevalue(self, line, preceeder):
        for i in range(0, len(line)):
            if preceeder in line[i]:
                return float(line[i + 1])
        return None

    def extractvalues(self, lines, index):
        reslist = list()
        if '[Device: id=0]' in lines[index]:
            reslist.append(self.parsevalue(lines[index].split(), 'RX'))
        if '[Device: id=1]' in lines[index + 1]:
            reslist.append(self.parsevalue(lines[index].split(), 'RX'))
        if '[Device: id=0]' in lines[index + 2]:
            reslist.append(self.parsevalue(lines[index].split(), 'TX'))
        if '[Device: id=1]' in lines[index + 3]:
            reslist.append(self.parsevalue(lines[index].split(), 'TX'))

        if None not in reslist and len(reslist == 4):
            return reslist
        else:
            return None

    def evaluate(self, lines, index):
        result = True
        vallist = self.initvalues()
        avgcounter = 0
        firstvalueskip = True
        firstminmax = True
        for i in range(index, len(lines)):
            if not result:
                break
            # if '[FATAL]' in lines[i] or '[ERROR]' in lines[i] or '[WARN]' in lines[i]:
            #     print'--line of interest: ' + lines[i]
            #     self.summarylog.write('line of interest: ' + lines[i] + '\n')
            # elif 'Saving histogram to' in lines[i]:
            #     for j in range(i, len(lines)):
            #         self.summarylog.write(lines[j])
            #     break
            if self.checkalerts(lines, i) is False:
                break
            elif '[Device: id=0]' in lines[i]:
                if firstvalueskip is True:
                    i += 3
                    firstvalueskip = False
                    continue
                else:
                    tmpval = self.extractvalues(lines, i)
                    if tmpval is not None:
                        # call adjust values here
                        vallist = self.adjustvalues(vallist, tmpval[2], tmpval[3], tmpval[0], tmpval[1], firstminmax)
                        firstminmax = False
                        avgcounter += 1
                        result = result and (tmpval[0] > self.resulttolorance * tmpval[3] and
                                             tmpval[1] > self.resulttolorance * tmpval[2])
        vallist[0][self.valueindex['txavg']] /= float(avgcounter)  # tx1 avg
        vallist[0][self.valueindex['rxavg']] /= float(avgcounter)  # rx1 avg
        vallist[1][self.valueindex['txavg']] /= float(avgcounter)  # tx2 avg
        vallist[1][self.valueindex['rxavg']] /= float(avgcounter)  # rx2 avg

        self.summarylog.write(
            'TX values of device 1 are:\n MAX = ' + str(vallist[0][self.valueindex['txmax']]) + '\n MIN = ' + str(
                vallist[0][self.valueindex['txmin']]) + '\n AVG = ' + str(vallist[0][self.valueindex['txavg']]) + '\n')
        self.summarylog.write(
            'RX values of device 1 are:\n MAX = ' + str(vallist[0][self.valueindex['rxmax']]) + '\n MIN = ' + str(
                vallist[0][self.valueindex['rxmin']]) + '\n AVG = ' + str(vallist[0][self.valueindex['rxavg']]) + '\n')
        self.summarylog.write(
            'TX values of device 2 are:\n MAX = ' + str(vallist[1][self.valueindex['txmax']]) + '\n MIN = ' + str(
                vallist[1][self.valueindex['txmin']]) + '\n AVG = ' + str(vallist[1][self.valueindex['txavg']]) + '\n')
        self.summarylog.write(
            'RX values of device 2 are:\n MAX = ' + str(vallist[1][self.valueindex['rxmax']]) + '\n MIN = ' + str(
                vallist[1][self.valueindex['rxmin']]) + '\n AVG = ' + str(vallist[1][self.valueindex['rxavg']]) + '\n')
        self.summarylog.write(
            'Conclusion: has RX value always been at least ' + str(self.resulttolorance * 100) + ' % of TX on both ways? : ' + str(
                result) + '\n')
        self.assertTrue(result,
                        msg='This means that the RX values were not over 90 percent of TX values at all times on both ways')

    def adjustvalues(self, vallist, tx1value, tx2value, rx1value, rx2value, firstrun):
        if tx1value > vallist[0][self.valueindex['txmax']]:
            vallist[0][self.valueindex['txmax']] = tx1value
            if firstrun is True:
                vallist[0][self.valueindex['txmin']] = vallist[0][self.valueindex['txmax']]
        if tx1value < vallist[0][self.valueindex['txmin']]:
            vallist[0][self.valueindex['txmin']] = tx1value
        if rx1value > vallist[0][self.valueindex['rxmax']]:
            vallist[0][self.valueindex['rxmax']] = rx1value
            if firstrun is True:
                vallist[0][self.valueindex['rxmin']] = vallist[0][self.valueindex['rxmax']]
        if rx1value < vallist[0][self.valueindex['rxmin']]:
            vallist[0][self.valueindex['rxmin']] = rx1value

        if tx2value > vallist[1][self.valueindex['txmax']]:
            vallist[1][self.valueindex['txmax']] = tx2value
            if firstrun is True:
                vallist[1][self.valueindex['txmin']] = vallist[1][self.valueindex['txmax']]
        if tx2value < vallist[1][self.valueindex['txmin']]:
            vallist[1][self.valueindex['txmin']] = tx2value
        if rx2value > vallist[1][self.valueindex['rxmax']]:
            vallist[1][self.valueindex['rxmax']] = rx2value
            if firstrun is True:
                vallist[1][self.valueindex['rxmin']] = vallist[1][self.valueindex['rxmax']]
        if rx2value < vallist[1][self.valueindex['rxmin']]:
            vallist[1][self.valueindex['rxmin']] = rx1value

        vallist[0][self.valueindex['txavg']] += tx1value
        vallist[0][self.valueindex['rxavg']] += rx1value
        vallist[1][self.valueindex['txavg']] += tx2value
        vallist[1][self.valueindex['rxavg']] += rx2value

        return vallist


class TestSimpleUDP(TerminatingTest):
    logname = 'udpSimpleTestLog'
    # testlog = open(logname, 'w')
    casename = 'udp simple'

    def executetest(self):
        return subprocess.Popen([
            './moongen-simple', 'start', 'udp-simple:0:1:rate=1000mbit/s,ratePattern=poisson'],
            stdout=self.testlog, cwd=self.path)

    # def evaluate(self, lines, index):
    #     # parse the log file, assert crateria
    #     # self.testlog = open(self.logname, 'r')
    #     # lines = self.testlog.readlines()
    #     # self.testlog.close()
    #     result = True
    #     for i in range(index, len(lines)):
    #         if not result:
    #             break
    #         if '[FATAL]' in lines[i]:
    #             self.assertTrue(False, msg='FATAL error')
    #         # exit condition: found 0 usable devices
    #         # if 'Found 0 usable devices:' in lines[i]:
    #         #     self.assertTrue(False, msg='There are no usable devices')
    #         # make sure device: id=0
    #         if '[Device: id=0]' in lines[i]:
    #             # store value
    #             line1 = lines[i].split()
    #             for j in range(0, len(line1)):
    #                 if '[0m: ' in line1[j]:
    #                     txvalue = float(line1[j + 1])
    #                     if '[Device: id=1]' not in lines[i + 1]:
    #                         continue
    #                     line2 = lines[i + 1].split()
    #                     for k in range(0, len(line2)):
    #                         if '[0m: ' in line2[k]:
    #                             rxvalue = float(line2[k + 1])
    #                             self.checkvaluesarezero(txvalue, rxvalue)
    #                             result = result and (rxvalue > txvalue * self.resulttolorance)
    #                             break
    #                     break
    #     self.assertTrue(result,
    #                     msg='This means that the RX values were not over %d \% of TX values at all times'
    #                         % (self.resulttolorance * 100.0))


class TestLoadLatency(TerminatingTest):
    logname = 'loadlatencylog'
    # testlog = open(logname, 'w')
    casename = 'load latency'

    def executetest(self):
        return subprocess.Popen([
            './moongen-simple', 'start', 'load-latency:0:1:rate=1000,timeLimit=10m'],
            stdout=self.testlog, cwd=self.path)

    # def evaluate(self, lines, index):
    #     result = True
    #     for i in range(index, len(lines)):
    #         if not result:
    #             break
    #         if '[Device: id=0]' in lines[i]:
    #             line1 = lines[i].split()
    #             for j in range(0, len(line1)):
    #                 if 'TX:' in line1[j]:
    #                     txvalue = float(line1[j + 1])
    #                     if '[Device: id=1]' not in lines[i + 1]:
    #                         continue
    #                     line2 = lines[i + 1].split()
    #                     for k in range(0, len(line2)):
    #                         if 'RX:' in line2[k]:
    #                             rxvalue = float(line2[k + 1])
    #                             self.checkvaluesarezero(txvalue, rxvalue)
    #                             result = result and (rxvalue > txvalue * self.resulttolorance)
    #                             break
    #                     break
    #     self.assertTrue(result,
    #                     msg='This means that the RX values were not over %d \% of TX values at all times'
    #                         % (self.resulttolorance * 100.0))


class TestUdpLoad(TerminatingTest):
    logname = 'udploadlog'
    # testlog = open(logname, 'w')
    casename = 'udp load'

    def executetest(self):
        return subprocess.Popen([
            './moongen-simple', 'start', 'udp-load:0:1:rate=1mp/s,mode=all,timestamp'],
            stdout=self.testlog, cwd=self.path)


class TestQosForeground(TerminatingTest):
    logname = 'qosforegroundlog'
    # testlog = open(logname, 'w')
    casename = 'qos-foreground'

    def executetest(self):
        return subprocess.Popen([
            './moongen-simple', 'start', 'qos-foreground:0:1'],
            stdout=self.testlog, cwd=self.path)


class TestQosBackground(TerminatingTest):
    logname = 'qosbackgroundlog'
    casename = 'qos-background'

    def executetest(self):
        return subprocess.Popen([
            './moongen-simple', 'start', 'qos-background:0:1'],
            stdout=self.testlog, cwd=self.path)


class TestDeviceStatistics(TerminatingTest):
    logname = 'devicestatisticslog'
    casename = 'device statistics'

    def executetest(self):
        return subprocess.Popen([
            './build/MoonGen', './examples/device-statistics.lua', '0', '1'],
            stdout=self.testlog, cwd=self.path)


class TestL2LoadLatency(TwoWayTerminatingTest):
    logname = 'l2loadlatencylog'
    casename = 'L2 Load Latency'

    def executetest(self):
        return subprocess.Popen([
            './build/MoonGen', './examples/l2-load-latency.lua', '0', '1'],
            stdout=self.testlog, cwd=self.path)

    # this class needs to read the log differently, it prints the values pairwise


class TestL2PoissonLoadLatency(TerminatingTest):
    logname = 'l2poissonloadlatencylog'
    casename = 'L2 Poisson Load Latency'

    def executetest(self):
        return subprocess.Popen([
            './build/MoonGen', './examples/l2-poisson-load-latency.lua', '0', '1'],
            stdout=self.testlog, cwd=self.path)


class TestL3LoadLatency(TerminatingTest):
    logname = 'l3loadlatencylog'
    casename = 'L3 Load Latency'

    def executetest(self):
        return subprocess.Popen([
            './build/MoonGen', './examples/l3-load-latency.lua', '0', '1'],
            stdout=self.testlog, cwd=self.path)


class TestTimeStampCapabilities(BindDevices):
    reqpasses = 2
    logname = 'timestamplog'
    waitinterval = 2

    # testlog = open(logname, 'w')

    # test timestamp between NICs
    def runTest(self):
        print("Testing MoonGen TimeStamp Capabilities of devices: %s and %s"
              % (self.devicelist[0], self.devicelist[1]))
        p = subprocess.Popen(['./build/MoonGen',
                              './examples/timestamping-tests/test-timestamping-capabilities.lua',
                              '0', '1'], stdout=self.testlog, cwd=self.path)
        while p.poll() is None:
            time.sleep(self.waitinterval)
            sys.stdout.write('.')
            sys.stdout.flush()
        print''
        self.testlog.close()
        self.testlog = open(self.logname, 'r')
        lines = self.testlog.readlines()
        testquant = 0
        errorcounter = 0
        for index in range(0, len(lines)):
            if 'Testing' in lines[index]:
                testquant += 1
            if 'Error' in lines[index] or 'ERROR' in lines[index]:
                errorcounter += 1
                print 'Found error in a line!'
                print(lines[index])
                target = ''
                out = ''
                backtrack = 0
                while target != '\n':
                    out = target
                    target = lines[index - backtrack]
                    backtrack += 1
                print'Following case failed:'
                print(out)

        print'Timestamping conducted %d tests, %d errors came up' % (testquant, errorcounter)
        self.assertTrue(testquant - errorcounter > self.reqpasses,
                        msg='Selected devices have passed less than %d tests in Test Timestamping Capabilities'
                            % self.reqpasses)
