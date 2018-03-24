#!/usr/bin/env python

"""
(c) 2018 Mario Orlandi, Brainstorm S.n.c.
"""

__author__    = "Mario Orlandi"
__version__   = "1.0.0"
__copyright__ = "Copyright (c) 2018, Brainstorm S.n.c."
__license__   = "GPL"

REPO = "https://github.com/morlandi/rotate_files"

import sys
import os
import logging
import datetime
import argparse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DAILY = './daily'
WEEKLY = './weekly'
MONTHLY = './monthly'
YEARLY = './yearly'
QUARANTINE = './quarantine'


class DatedFile(object):

    filename = None
    filedate = None
    age = None

    def __init__(self, filename):
        self.filename = filename
        self.parse_filedate()
        if self.filedate is not None:
            self.age = (datetime.date.today() - self.filedate).days

    def parse_filedate(self):
        if self.filedate is None:
            # try "2018-03-22_..."
            try:
                self.filedate = datetime.datetime.strptime(self.filename[:10], "%Y-%m-%d").date()
            except:
                pass
        if self.filedate is None:
            # try "1521766816_2018_03_23_..."
            try:
                n = self.filename.find('_')
                self.filedate = datetime.datetime.strptime(self.filename[n+1:n+1+10], "%Y_%m_%d").date()
            except:
                pass

    def __str__(self):
        if self.filedate is None:
            return self.filename
        return '%s [dated:%s, age=%d, fdow=%d, fdom=%d, fdoy=%d]' % (
            self.filename,
            self.filedate,
            int(self.age),
            int(self.fdow),
            int(self.fdom),
            int(self.fdoy),
        )

    def is_dated(self):
        return self.filedate is not None

    @property
    def fdow(self):
        """
        First day of week ?
        """
        if self.filedate is None:
            return False
        return self.filedate.weekday() == 0

    @property
    def fdom(self):
        """
        First day of month ?
        """
        if self.filedate is None:
            return False
        return self.filedate.day == 1

    @property
    def fdoy(self):
        """
        First day of year ?
        """
        if self.filedate is None:
            return False
        return self.filedate.month == 1 and self.filedate.day == 1

    def move_to(self, source_folder, target_folder):
        """
        Move dated file from source to target folder
        """
        assert(self.is_dated())
        logger.info('Moving file "%s" from "%s" to "%s"' % (self.filename, source_folder, target_folder))
        os.rename(os.path.join(source_folder, self.filename), os.path.join(target_folder, self.filename))

    def to_quarantine(self, source_folder):
        """
        Move dated file to quarantine.
        Target filename will be prepended with current date,
        so we always know when this happened.
        """
        assert(self.is_dated())
        target_filename = "%s_____%s" % (datetime.date.today().strftime('%Y-%m-%d'), self.filename)
        logger.info('Moving file "%s" from "%s" to quarantine' % (self.filename, source_folder))
        os.rename(os.path.join(source_folder, self.filename), os.path.join(QUARANTINE, target_filename))

    def destroy(self, source_folder):
        """
        Remove the file.
        We only accept this whan source folder is QUARANTINE
        """
        assert(source_folder == QUARANTINE)
        logger.info('Erasing file "%s" from "%s"' % (self.filename, source_folder))
        os.unlink(os.path.join(source_folder, self.filename))


def collect_dated_files(source_folder, min_age):
    """
    """
    files = []
    filenames = os.listdir(source_folder)
    for filename in filenames:
        file_obj = DatedFile(filename)
        if file_obj.is_dated() and file_obj.age >= min_age:
            files.append(file_obj)
    return files


def rotate_daily():
    logger.info('Rotating daily files ...')
    files = collect_dated_files(DAILY, 7)
    errors = 0
    for file_obj in files:
        logger.debug(file_obj)
        try:
            if file_obj.fdow or file_obj.fdom:
                file_obj.move_to(DAILY, WEEKLY)
            else:
                file_obj.to_quarantine(DAILY)
        except Exception as e:
            logger.error(str(e), exc_info=True)
            errors += 1
    return errors


def rotate_weekly():
    logger.info('Rotating weekly files ...')
    files = collect_dated_files(WEEKLY, 31)
    errors = 0
    for file_obj in files:
        logger.debug(file_obj)
        try:
            if file_obj.fdom:
                file_obj.move_to(WEEKLY, MONTHLY)
            else:
                file_obj.to_quarantine(WEEKLY)
        except Exception as e:
            logger.error(str(e), exc_info=True)
            errors += 1
    return errors


def rotate_monthly():
    logger.info('Rotating monthly files ...')
    files = collect_dated_files(MONTHLY, 365)
    errors = 0
    for file_obj in files:
        logger.debug(file_obj)
        try:
            if file_obj.fdoy:
                file_obj.move_to(MONTHLY, YEARLY)
            else:
                file_obj.to_quarantine(MONTHLY)
        except Exception as e:
            logger.error(str(e), exc_info=True)
            errors += 1
    return errors


def cleanup_quarantine():
    files = collect_dated_files(QUARANTINE, 31)
    for file in files:
        file.destroy(QUARANTINE)


def setup_logger(verbosity):
    """
    Set logger level based on verbosity option
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(module)s| %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if verbosity == 0:
        logger.setLevel(logging.WARN)
    elif verbosity == 1:  # default
        logger.setLevel(logging.INFO)
    elif verbosity > 1:
        logger.setLevel(logging.DEBUG)

    # verbosity 3: also enable all logging statements that reach the root logger
    if verbosity > 2:
        logging.getLogger().setLevel(logging.DEBUG)


def main(args):

    # Parse command line
    parser = argparse.ArgumentParser(description='Helper script to rotate backup files; see "%s" for instructions' % REPO)
    parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2, 3], default=1,
        help="Verbosity level. (default: 1)")
    options = parser.parse_args()
    # print('Result:',  vars(options))

    setup_logger(options.verbosity)

    errors = 0
    try:
        logger.info('File rotation started')

        # Select the folder where the script lives as cwd
        filepath = os.path.dirname(os.path.realpath(__file__))
        os.chdir(filepath)
        logger.info('cwd: ' + os.getcwd())

        # Create working folders
        if os.path.exists(DAILY):
            for folder in [WEEKLY, MONTHLY, YEARLY, QUARANTINE, ]:
                if not os.path.exists(folder):
                    logger.info('Creating folder "%s"' % folder)
                    os.makedirs(folder)

        # Rotate files
        errors += rotate_daily()
        errors += rotate_weekly()
        errors += rotate_monthly()

        cleanup_quarantine()

    except Exception as e:
        logger.error(str(e), exc_info=True)
        errors += 1
    finally:
        logger.info('File rotation completed ' + ('successfully' if errors <= 0 else 'with errors'))

    return 1


if __name__ == "__main__":
    # execute only if run as a script
    main(sys.argv[1:])
