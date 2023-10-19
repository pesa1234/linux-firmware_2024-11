#!/usr/bin/python3

import os, re, sys
from io import open


def list_whence():
    with open("WHENCE", encoding="utf-8") as whence:
        for line in whence:
            match = re.match(r'(?:RawFile|File|Source):\s*"(.*)"', line)
            if match:
                yield match.group(1)
                continue
            match = re.match(r"(?:RawFile|File|Source):\s*(\S*)", line)
            if match:
                yield match.group(1)
                continue
            match = re.match(
                r"Licen[cs]e: (?:.*\bSee (.*) for details\.?|(\S*))\n", line
            )
            if match:
                if match.group(1):
                    for name in re.split(r", | and ", match.group(1)):
                        yield name
                    continue
                if match.group(2):
                    # Just one word - may or may not be a filename
                    if not re.search(
                        r"unknown|distributable", match.group(2), re.IGNORECASE
                    ):
                        yield match.group(2)
                        continue


def list_whence_files():
    with open("WHENCE", encoding="utf-8") as whence:
        for line in whence:
            match = re.match(r"(?:RawFile|File):\s*(.*)", line)
            if match:
                yield match.group(1).replace("\ ", " ").replace('"', "")
                continue


def list_links_list():
    with open("WHENCE", encoding="utf-8") as whence:
        for line in whence:
            match = re.match(r"Link:\s*(.*)", line)
            if match:
                linkname, target = match.group(1).split("->")

                linkname = linkname.strip().replace("\ ", " ").replace('"', "")
                target = target.strip().replace("\ ", " ").replace('"', "")

                # Link target is relative to the link
                target = os.path.join(os.path.dirname(linkname), target)
                target = os.path.normpath(target)

                yield (linkname, target)
                continue


def list_git():
    with os.popen("git ls-files") as git_files:
        for line in git_files:
            yield line.rstrip("\n")


def main():
    ret = 0
    whence_list = list(list_whence())
    whence_files = list(list_whence_files())
    links_list = list(list_links_list())
    known_files = set(name for name in whence_list if not name.endswith("/")) | set(
        [
            ".gitignore",
            ".codespell.cfg",
            ".gitlab-ci.yml",
            ".pre-commit-config.yaml",
            "build_packages.py",
            "check_whence.py",
            "configure",
            "Makefile",
            "README.md",
            "copy-firmware.sh",
            "WHENCE",
            "Dockerfile",
            "contrib/templates/debian.changelog",
            "contrib/templates/debian.control",
            "contrib/templates/debian.copyright",
            "contrib/templates/rpm.spec",
            "contrib/process_linux_firmware.py",
        ]
    )
    known_prefixes = set(name for name in whence_list if name.endswith("/"))
    git_files = set(list_git())

    for name in set(name for name in whence_files if name.endswith("/")):
        sys.stderr.write("E: %s listed in WHENCE as File, but is directory\n" % name)
        ret = 1

    for name in set(fw for fw in whence_files if whence_files.count(fw) > 1):
        sys.stderr.write("E: %s listed in WHENCE twice\n" % name)
        ret = 1

    for name in set(link for link in whence_files if os.path.islink(link)):
        sys.stderr.write("E: %s listed in WHENCE as File, but is a symlink\n" % name)
        ret = 1

    for name in set(link[0] for link in links_list if os.path.islink(link[0])):
        sys.stderr.write("E: %s listed in WHENCE as Link, is in tree\n" % name)
        ret = 1

    for name in sorted(list(known_files - git_files)):
        sys.stderr.write("E: %s listed in WHENCE does not exist\n" % name)
        ret = 1

    # A link can point to another link, or to a file...
    valid_targets = set(link[0] for link in links_list) | git_files

    # ... or to a directory
    for target in set(valid_targets):
        dirname = target
        while True:
            dirname = os.path.dirname(dirname)
            if dirname == "":
                break
            valid_targets.add(dirname)

    for name, target in sorted(links_list):
        if target not in valid_targets:
            sys.stderr.write(
                "E: target %s of link %s in WHENCE" " does not exist\n" % (target, name)
            )
            ret = 1

    for name in sorted(list(git_files - known_files)):
        # Ignore subdirectory changelogs and GPG detached signatures
        if name.endswith("/ChangeLog") or (
            name.endswith(".asc") and name[:-4] in known_files
        ):
            continue

        # Ignore unknown files in known directories
        for prefix in known_prefixes:
            if name.startswith(prefix):
                break
        else:
            sys.stderr.write("E: %s not listed in WHENCE\n" % name)
            ret = 1
    return ret


if __name__ == "__main__":
    sys.exit(main())
