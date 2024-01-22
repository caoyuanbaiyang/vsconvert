import os
import pipes

import paramiko

SSH_CONNECTION_CACHE = {}
SFTP_CONNECTION_CACHE = {}


class Runner(object):
    def __init__(self,
                 private_key_file='id_rsa',
                 timeout=30):
        self.private_key_file = private_key_file
        self.timeout = timeout


class Connection(object):
    """ SSH based connections with Paramiko """

    def __init__(self, runner, host, port, user, password):

        self.ssh = None
        self.sftp = None
        self.runner = runner
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def _cache_key(self):
        return "%s__%s__" % (self.host, self.user)

    def connect(self):
        cache_key = self._cache_key()
        if cache_key in SSH_CONNECTION_CACHE:
            self.ssh = SSH_CONNECTION_CACHE[cache_key]
        else:
            self.ssh = SSH_CONNECTION_CACHE[cache_key] = self._connect_uncached()
        return self

    def _connect_uncached(self):
        """ activates the connection object """

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        allow_agent = True
        if self.password is not None:
            allow_agent = False
        try:
            if self.runner.private_key_file:
                key_filename = os.path.expanduser(self.runner.private_key_file)
            else:
                key_filename = None
            ssh.connect(self.host, username=self.user, allow_agent=allow_agent, look_for_keys=True,
                        key_filename=key_filename, password=self.password,
                        timeout=self.runner.timeout, port=self.port)
        except Exception as e:
            msg = str(e)
            if "PID check failed" in msg:
                raise "paramiko version issue, please upgrade paramiko on the machine running ansible"
            elif "Private key file is encrypted" in msg:
                msg = 'ssh %s@%s:%s : %s\nTo connect as a different user, use -u <username>.' % (
                    self.user, self.host, self.port, msg)
                raise Exception(msg)
            else:
                raise Exception(msg)

        return ssh

    def exec_command(self, cmd, executable='/bin/sh'):
        """ run a command on the remote host """

        bufsize = 4096
        try:
            chan = self.ssh.get_transport().open_session()
        except Exception as e:
            msg = "Failed to open session"
            if len(str(e)) > 0:
                msg += ": %s" % str(e)
            raise msg

        if executable:
            quoted_command = executable + ' -c ' + pipes.quote(cmd)
        else:
            quoted_command = cmd
        print(f"EXEC {quoted_command}  host:{self.host}")
        chan.exec_command(quoted_command)

        stdout = ''.join(chan.makefile('r', bufsize))
        stderr = ''.join(chan.makefile_stderr('r', bufsize))
        return chan.recv_exit_status(), '', stdout, stderr

    def put_file(self, in_path, out_path):
        """ transfer a file from local to remote """
        print("PUT %s TO %s" % (in_path, out_path))
        if not os.path.exists(in_path):
            raise "file or module does not exist: %s" % in_path
        try:
            self.sftp = self.ssh.open_sftp()
        except Exception as e:
            raise "failed to open a SFTP connection (%s)" % e
        try:
            self.sftp.put(in_path, out_path)
        except IOError:
            raise "failed to transfer file to %s" % out_path

    def _connect_sftp(self):
        cache_key = "%s__%s__" % (self.host, self.user)
        if cache_key in SFTP_CONNECTION_CACHE:
            return SFTP_CONNECTION_CACHE[cache_key]
        else:
            result = SFTP_CONNECTION_CACHE[cache_key] = self.connect().ssh.open_sftp()
            return result

    def fetch_file(self, in_path, out_path):
        """ save a remote file to the specified path """
        print("FETCH %s TO %s" % (in_path, out_path), host=self.host)
        try:
            self.sftp = self._connect_sftp()
        except Exception as e:
            raise ("failed to open a SFTP connection (%s)", e)
        try:
            self.sftp.get(in_path, out_path)
        except IOError:
            raise "failed to transfer file from %s" % in_path

    def close(self):
        """ terminate the connection """
        cache_key = self._cache_key()
        SSH_CONNECTION_CACHE.pop(cache_key, None)
        SFTP_CONNECTION_CACHE.pop(cache_key, None)
        if self.sftp is not None:
            self.sftp.close()
        self.ssh.close()


# r = Runner()
# c = Connection(r, '58.1.10.70', 22, 'intclns', '1')
# c.connect()
# exit_status, n, stdout, stderr = c.exec_command('ls sdfas')
# print(exit_status, n, stdout, stderr)
# c.close()
