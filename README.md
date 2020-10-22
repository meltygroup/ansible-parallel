# ansible-parallel

TL;DR:

```bash
pip install ansible-parallel
ansible-parallel *.yml
```

Executes multiple ansible playbooks in parallel.

For my usage, running sequentially (using a `site.yml` containing
multiple `import_playbook`) takes 30mn, running in parallel takes
10mn.


## Usage

`ansible-parallel` runs like `ansible-playbook` but accepts multiple
playbooks. All remaining options are passed to `ansible-playbook` so
feel free to run `ansible-parallel --check *.yml` for example.


## Example

```bash
$ ansible-parallel *.yml
# Playbook playbook-webs.yml, ran in 123s

web1.meltygroup.com         : ok=51   changed=0    unreachable=0    failed=0    skipped=12   rescued=0    ignored=0
web2.meltygroup.com         : ok=51   changed=0    unreachable=0    failed=0    skipped=12   rescued=0    ignored=0
web3.meltygroup.com         : ok=51   changed=0    unreachable=0    failed=0    skipped=12   rescued=0    ignored=0


# Playbook playbook-staging.yml, ran in 138s

staging1.meltygroup.com         : ok=64   changed=6    unreachable=0    failed=0    skipped=18   rescued=0    ignored=0


# Playbook playbook-gitlab.yml, ran in 179s

gitlab-runner1.meltygroup.com         : ok=47   changed=0    unreachable=0    failed=0    skipped=13   rescued=0    ignored=0
gitlab-runner2.meltygroup.com         : ok=47   changed=0    unreachable=0    failed=0    skipped=13   rescued=0    ignored=0
gitlab-runner3.meltygroup.com         : ok=47   changed=0    unreachable=0    failed=0    skipped=13   rescued=0    ignored=0
gitlab.meltygroup.com                 : ok=51   changed=0    unreachable=0    failed=0    skipped=12   rescued=0    ignored=0


# Playbook playbook-devs.yml, ran in 213s

dev1.meltygroup.com             : ok=121  changed=0    unreachable=0    failed=0    skipped=22   rescued=0    ignored=0
dev2.meltygroup.com             : ok=121  changed=0    unreachable=0    failed=0    skipped=22   rescued=0    ignored=0
```


## Known alternatives

### ansible-pull

ansible-parallel is only good if you want to keep the push behavior of
Ansible, but if you're here you may have a lot of playbooks, and
switching to
[ansible-pull](https://docs.ansible.com/ansible/latest/cli/ansible-pull.html)
with a proper reporting system like
[ARA](https://github.com/ansible-community/ara)


### xargs

A quick and dirty way of doing it in 3 lines of bash:

```
ls -1 *.yml | xargs -n1 -P16 sh -c 'ansible-playbook "$$0" > "$$0.log"' ||:
grep -B1 "^\(changed\|fatal\|failed\):" *.log
echo *.yml.log | xargs -n1 sed -n -e '/^PLAY RECAP/,$$p'
```
