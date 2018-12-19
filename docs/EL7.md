# Steps to get this working with EL7

## Modules

You will likely need to track down more module dependencies, though this is what
I used.

`Puppetfile`

```ruby
mode 'apache',
  :git => 'https://github.com/puppetlabs/puppetlabs-apache.git',
  :ref => '3.4.0'

mod 'apt',
  :git => 'https://github.com/puppetlabs/puppetlabs-apt.git',
  :ref => '6.2.1'

mod 'concat',
  :git => 'https://github.com/puppetlabs/puppetlabs-concat.git',
  :ref => '5.1.0'

mod 'epel',
  :git => 'https://github.com/stahnma/puppet-module-epel.git',
  :ref => '1.3.1'

mod 'firewall',
  :git => 'https://github.com/puppetlabs/puppetlabs-firewall.git',
  :ref => '1.14.0'

mod 'inifile',
  :git => 'https://github.com/puppetlabs/puppetlabs-inifile.git',
  :ref => '2.4.0'

mod 'postgresql',
  :git => 'https://github.com/puppetlabs/puppet-postgresql.git',
  :ref => '5.11.0'

mod 'puppetdb',
  :git => 'https://github.com/puppetlabs/puppetlabs-puppetdb.git',
  :ref => '7.1.0'

mod 'puppetboard',
  :git => 'https://github.com/voxpupuli/puppet-puppetboard.git',
  :ref => 'v5.0.0'

mod 'python',
  :git => 'https://github.com/voxpupuli/puppet-python.git',
  :ref => 'v2.2.2'

mod 'selinux',
  :git => 'https://github.com/ghoneycutt/puppet-module-selinux.git',
  :ref => 'v2.2.0'

mod 'stdlib',
  :git => 'https://github.com/puppetlabs/puppetlabs-stdlib.git',
  :ref => '5.1.0'

mod 'translate',
  :git => 'https://github.com/puppetlabs/puppetlabs-translate.git',
  :ref => '1.2.0'
```

## Manifests

### Role

`role/manifests/puppetboard.pp`

```puppet
# @summary Role for puppetboard
#
class role::puppetboard {

  include ::profile::puppetboard
}
```

### Profile

`profile/manifests/puppetboard.pp`

```puppet
# Class: profile::puppetboard
#
# Puppetboard is a WebUI to inspect PuppetDB
#
class profile::puppetboard {

  include ::apache

  $puppetboard_certname = $trusted['certname']
  $ssl_dir = '/etc/httpd/ssl'

  file { $ssl_dir:
    ensure => 'directory',
    owner  => 'root',
    group  => 'root',
    mode   => '0755',
  }

  file { "${ssl_dir}/certs":
    ensure => 'directory',
    owner  => 'root',
    group  => 'root',
    mode   => '0755',
  }

  file { "${ssl_dir}/private_keys":
    ensure => 'directory',
    owner  => 'root',
    group  => 'root',
    mode   => '0750',
  }

  file { "${ssl_dir}/certs/ca.pem":
    ensure => 'file',
    owner  => 'root',
    group  => 'root',
    mode   => '0644',
    source => "${::settings::ssldir}/certs/ca.pem",
    before => Class['::puppetboard'],
  }

  file { "${ssl_dir}/certs/${puppetboard_certname}.pem":
    ensure => 'file',
    owner  => 'root',
    group  => 'root',
    mode   => '0644',
    source => "${::settings::ssldir}/certs/${puppetboard_certname}.pem",
    before => Class['::puppetboard'],
  }

  file { "${ssl_dir}/private_keys/${puppetboard_certname}.pem":
    ensure => 'file',
    owner  => 'root',
    group  => 'root',
    mode   => '0644',
    source => "${::settings::ssldir}/private_keys/${puppetboard_certname}.pem",
    before => Class['::puppetboard'],
  }

  class { '::puppetboard':
    groups              => 'root',
    manage_git          => true,
    manage_virtualenv   => true,
    manage_selinux      => false,
    puppetdb_host       => 'puppetdb.example.com',
    puppetdb_port       => 8081,
    puppetdb_key        => "${ssl_dir}/private_keys/${puppetboard_certname}.pem",
    puppetdb_ssl_verify => "${ssl_dir}/certs/ca.pem",
    puppetdb_cert       => "${ssl_dir}/certs/${puppetboard_certname}.pem",
    reports_count       => 40,
  }

  class { '::apache::mod::wsgi':
    wsgi_socket_prefix => '/var/run/wsgi',
  }

  class { '::puppetboard::apache::vhost':
    vhost_name => 'puppetboard.example.com',
    port       => 80,
  }
}
```

## Hiera data

```yaml
---

# Personal preference, you don't *need* this.
puppetboard::enable_catalog: true

python::dev: true

selinux::mode: permissive
```

I put this in `data/role/puppetboard.yaml` with `hiera.yaml` like the
following, though you could put this under certname or wherever you see
fit.

```yaml
---
version: 5
defaults:
  # The default value for "datadir" is "data" under the same directory as the hiera.yaml
  # file (this file)
  # When specifying a datadir, make sure the directory exists.
  # See https://puppet.com/docs/puppet/latest/environments_about.html for further details on environments.
  # datadir: data
  # data_hash: yaml_data
hierarchy:
  - name: "Per-node data (yaml version)"
    path: "nodes/%{::trusted.certname}.yaml"
  - name: "Role data"
    paths:
      - "role/%{facts.role}.yaml"
  - name: "Other YAML hierarchy levels"
    paths:
      - "common.yaml"
```
