/*
   Copyright 2005-2010 Jakub Kruszona-Zawadzki, Gemius SA, 2013 Skytechnology sp. z o.o..

   This file was part of MooseFS and is part of LizardFS.

   LizardFS is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, version 3.

   LizardFS is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with LizardFS  If not, see <http://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "common/metadata.h"
#include "common/slogger.h"
#include "common/strerr.h"
#include "master/chunks.h"
#include "master/filesystem.h"
#include "metarestore/merger.h"
#include "metarestore/restore.h"

#define STR_AUX(x) #x
#define STR(x) STR_AUX(x)
const char id[]="@(#) version: " STR(PACKAGE_VERSION_MAJOR) "." STR(PACKAGE_VERSION_MINOR) "." STR(PACKAGE_VERSION_MICRO) ", written by Jakub Kruszona-Zawadzki";

#define MAXIDHOLE 10000

uint64_t findfirstlogversion(const std::string& fname) {
	uint8_t buff[50];
	int32_t s,p;
	uint64_t fv;
	int fd;

	fd = open(fname.c_str(), O_RDONLY);
	if (fd<0) {
		return 0;
	}
	s = read(fd,buff,50);
	close(fd);
	if (s<=0) {
		return 0;
	}
	fv = 0;
	p = 0;
	while (p<s && buff[p]>='0' && buff[p]<='9') {
		fv *= 10;
		fv += buff[p]-'0';
		p++;
	}
	if (p>=s || buff[p]!=':') {
		return 0;
	}
	return fv;
}

uint64_t findlastlogversion(const std::string& fname) {
	struct stat st;
	int fd;

	fd = open(fname.c_str(), O_RDONLY);
	if (fd < 0) {
		mfs_arg_syslog(LOG_ERR, "open failed: %s", strerr(errno));
		return 0;
	}
	fstat(fd, &st);

	size_t fileSize = st.st_size;

	const char* fileContent = (const char*) mmap(NULL, fileSize, PROT_READ, MAP_PRIVATE, fd, 0);
	if (fileContent == MAP_FAILED) {
		mfs_arg_syslog(LOG_ERR, "mmap failed: %s", strerr(errno));
		close(fd);
		return 0; // 0 counterintuitively means failure
	}
	uint64_t lastLogVersion = 0;
	// first LF is (should be) the last byte of the file
	if (fileSize == 0 || fileContent[fileSize - 1] != '\n') {
		mfs_arg_syslog(LOG_ERR, "truncated changelog (%s) (no LF at the end of the last line)",
				fname.c_str());
	} else {
		size_t pos = fileSize - 1;
		while (pos > 0) {
			--pos;
			if (fileContent[pos] == '\n') {
				break;
			}
		}
		char *endPtr = NULL;
		lastLogVersion = strtoull(fileContent + pos, &endPtr, 10);
		if (*endPtr != ':') {
			mfs_arg_syslog(LOG_ERR, "malformed changelog (%s) (expected colon after change number)",
					fname.c_str());
			lastLogVersion = 0;
		}
	}
	if (munmap((void*) fileContent, fileSize)) {
		mfs_arg_syslog(LOG_ERR, "munmap failed: %s", strerr(errno));
	}
	close(fd);
	return lastLogVersion;
}

int changelog_checkname(const char *fname) {
	const char *ptr = fname;
	if (strncmp(ptr,"changelog.",10)==0) {
		ptr+=10;
		if (*ptr>='0' && *ptr<='9') {
			while (*ptr>='0' && *ptr<='9') {
				ptr++;
			}
			if (strcmp(ptr,".mfs")==0) {
				return 1;
			}
		}
	} else if (strncmp(ptr,"changelog_ml.",13)==0) {
		ptr+=13;
		if (*ptr>='0' && *ptr<='9') {
			while (*ptr>='0' && *ptr<='9') {
				ptr++;
			}
			if (strcmp(ptr,".mfs")==0) {
				return 1;
			}
		}
	} else if (strncmp(ptr,"changelog_ml_back.",18)==0) {
		ptr+=18;
		if (*ptr>='0' && *ptr<='9') {
			while (*ptr>='0' && *ptr<='9') {
				ptr++;
			}
			if (strcmp(ptr,".mfs")==0) {
				return 1;
			}
		}
	}
	return 0;
}

void usage(const char* appname) {
	mfs_syslog(LOG_ERR, "invalid/missing arguments");
	fprintf(stderr, "restore metadata:\n"
			"\t%s [-c] [-k <checksum>] [-f] [-b] [-i] [-x [-x]] -m <meta data file> -o "
			"<restored meta data file> [ <change log file> [ <change log file> [ .... ]]\n"
			"dump metadata:\n"
			"\t%s [-i] -m <meta data file>\n"
			"autorestore:\n"
			"\t%s [-f] [-b] [-i] [-x [-x]] -a [-d <data path>]\n"
			"print version:\n"
			"\t%s -v\n"
			"\n"
			"-c - print checksum of the metadata\n"
			"-k - check checksum against given checksum\n"
			"-x - produce more verbose output\n"
			"-xx - even more verbose output\n"
			"-b - if there is any error in change logs then save the best possible metadata file\n"
			"-i - ignore some metadata structure errors (attach orphans to root, ignore names "
			"without inode, etc.)\n"
			"-f - force loading all changelogs", appname, appname, appname, appname);
}

int main(int argc,char **argv) {
	int ch;
	uint8_t vl=0;
	bool autorestore = false;
	int savebest = 0;
	int ignoreflag = 0;
	int forcealllogs = 0;
	bool printhash = false;
	int status;
	int skip;
	std::string metaout, metadata, datapath;
	char *appname = argv[0];
	uint64_t firstlv,lastlv;
	std::unique_ptr<uint64_t> expectedChecksum;

	strerr_init();
	openlog(nullptr, LOG_PID | LOG_NDELAY, LOG_USER);

	while ((ch = getopt(argc, argv, "fck:vm:o:d:abxih:?")) != -1) {
		switch (ch) {
			case 'v':
				printf("version: %u.%u.%u",
						PACKAGE_VERSION_MAJOR, PACKAGE_VERSION_MINOR, PACKAGE_VERSION_MICRO);
				return 0;
			case 'o':
				metaout = optarg;
				break;
			case 'm':
				metadata = optarg;
				break;
			case 'd':
				datapath = optarg;
				break;
			case 'x':
				vl++;
				break;
			case 'a':
				autorestore = true;
				break;
			case 'b':
				savebest=1;
				break;
			case 'i':
				ignoreflag=1;
				break;
			case 'f':
				forcealllogs=1;
				break;
			case 'c':
				printhash = true;
				break;
			case 'k':
				expectedChecksum.reset(new uint64_t);
				char* endPtr;
				*expectedChecksum = strtoull(optarg, &endPtr, 10);
				if (*endPtr != '\0') {
					mfs_arg_syslog(LOG_ERR, "invalid checksum: %s", optarg);
					return 1;
				}
				break;
			case '?':
			default:
				usage(argv[0]);
				return 1;
		}
	}
	argc -= optind;
	argv += optind;

	if ((!autorestore && (metadata.empty() || !datapath.empty()))
			|| (autorestore && (!metadata.empty() || !metaout.empty()))) {
		usage(appname);
		return 1;
	}

	restore_setverblevel(vl);

	if (autorestore) {
		if (datapath.empty()) {
			datapath = DATA_PATH;
		}
		// All candidates from the least to the most preferred one
		auto candidates{
			METADATA_ML_BACK_FILENAME ".1",
			METADATA_BACK_FILENAME ".1",
			METADATA_ML_BACK_FILENAME,
			METADATA_BACK_FILENAME,
			METADATA_FILENAME};
		std::string bestmetadata;
		uint64_t bestversion = 0;
		for (const char* candidate : candidates) {
			std::string metadata_candidate = std::string(datapath) + "/" + candidate;
			if (access(metadata_candidate.c_str(), F_OK) != 0) {
				continue;
			}
			try {
				uint64_t version = metadata_getversion(metadata_candidate.c_str());
				if (version >= bestversion) {
					bestversion = version;
					bestmetadata = metadata_candidate;
				}
			} catch (MetadataCheckException& ex) {
				mfs_arg_syslog(LOG_NOTICE, "skipping malformed metadata file %s: %s", candidate, ex.what());
			}
		}
		if (bestmetadata.empty()) {
			mfs_syslog(LOG_ERR, "error: can't find backed up metadata file !!!");
			return 1;
		}
		metadata = bestmetadata;
		metaout =  datapath + "/" METADATA_FILENAME;
		mfs_arg_syslog(LOG_NOTICE, "file %s will be used to restore the most recent metadata", metadata.c_str());
	}

	if (fs_init(metadata.c_str(), ignoreflag) != 0) {
		mfs_arg_syslog(LOG_ERR, "error: can't read metadata from file: %s", metadata.c_str());
		return 1;
	}
	if (fs_getversion() == 0) {
		// TODO(msulikowski) make it work! :)
		mfs_syslog(LOG_ERR,
				"error: applying changes to an empty metadata file (version 0) not supported!!!");
		return 1;
	}
	if (vl > 0) {
		mfs_arg_syslog(LOG_NOTICE, "loaded metadata with version %" PRIu64 "", fs_getversion());
	}

	if (autorestore) {
		std::vector<std::string> filenames;
		DIR *dd = opendir(datapath.c_str());
		if (!dd) {
			mfs_syslog(LOG_ERR, "can't open data directory");
			return 1;
		}
		rewinddir(dd);
		struct dirent *dp;
		while ((dp = readdir(dd)) != NULL) {
			if (changelog_checkname(dp->d_name)) {
				filenames.push_back(datapath + "/" + dp->d_name);
				firstlv = findfirstlogversion(filenames.back());
				lastlv = findlastlogversion(filenames.back());
				skip = ((lastlv<fs_getversion() || firstlv==0) && forcealllogs==0)?1:0;
				if (vl>0) {
					std::ostringstream oss;
					if (skip) {
						oss << "skipping changelog file: ";
					} else {
						oss << "using changelog file: ";
					}
					oss << filenames.back() << " (changes: ";
					if (firstlv > 0) {
						oss << firstlv;
					} else {
						oss << "???";
					}
					oss << " - ";
					if (lastlv > 0) {
						oss << lastlv;
					} else {
						oss << "???";
					}
					oss << ")";
					mfs_arg_syslog(LOG_NOTICE, "%s", oss.str().c_str());
				}
				if (skip) {
					filenames.pop_back();
				}
			}
		}
		closedir(dd);
		if (filenames.empty() && metadata == metaout) {
			mfs_syslog(LOG_NOTICE, "nothing to do, exiting without changing anything");
			return 0;
		}
		merger_start(filenames, MAXIDHOLE);
	} else {
		uint32_t pos;
		std::vector<std::string> filenames;

		for (pos=0 ; (int32_t)pos<argc ; pos++) {
			firstlv = findfirstlogversion(argv[pos]);
			lastlv = findlastlogversion(argv[pos]);
			skip = ((lastlv<fs_getversion() || firstlv==0) && forcealllogs==0)?1:0;
			if (vl>0) {
				std::ostringstream oss;
				if (skip) {
					oss << "skipping changelog file: ";
				} else {
					oss << "using changelog file: ";
				}
				oss << argv[pos] << " (changes: ";
				if (firstlv > 0) {
					oss << firstlv;
				} else {
					oss << "???";
				}
				oss << " - ";
				if (lastlv > 0) {
					oss << lastlv;
				} else {
					oss << "???";
				}
				oss << ")";
				mfs_arg_syslog(LOG_NOTICE, "%s", oss.str().c_str());
			}
			if (skip==0) {
				filenames.push_back(argv[pos]);
			}
		}
		merger_start(filenames, MAXIDHOLE);
	}

	status = merger_loop();

	if (status<0 && savebest==0) {
		return 1;
	}

	int returnStatus = 0;
	uint64_t checksum = fs_checksum(ChecksumMode::kForceRecalculate);
	if (printhash) {
		printf("%" PRIu64 "\n", checksum);
	}
	if (expectedChecksum) {
		returnStatus = *expectedChecksum == checksum ? 0 : 2;
		printf("%s\n", returnStatus ? "ERR" : "OK");
	}
	if (metaout.empty()) {
		fs_dump();
		chunk_dump();
	} else {
		mfs_arg_syslog(LOG_NOTICE, "store metadata into file: %s", metaout.c_str());
		fs_term(metaout.c_str());
	}
	return returnStatus;
}
