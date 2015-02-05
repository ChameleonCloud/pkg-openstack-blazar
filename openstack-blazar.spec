%global release_name juno
%global milestone rc2
%global commit e84096852f17ec14feb9b600ba5a07174fdab7ec

%global with_doc %{!?_without_doc:1}%{?_without_doc:0}

Name:           openstack-blazar
Version:        2014.2.1
Release:        1.git%{commit}%{?dist}
Summary:        OpenStack Reservation as a Service

License:        ASL 2.0
URL:            https://wiki.openstack.org/wiki/Blazar
Source0:        https://github.com/stackforge/blazar/archive/%{commit}.tar.gz

Source1:          openstack-blazar.logrotate
Source10:         openstack-blazar-api.service
Source11:         openstack-blazar-manager.service

Patch0001: 0001-remove-runtime-dep-on-python-pbr-in-blazar.patch
Patch0002: 0002-chameleon-make-blazar-work-with-ironic.patch

BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-pbr
BuildRequires:  python-d2to1

Requires:         python-alembic >= 0.6.4
Requires:         python-babel >= 1.3
Requires:         python-flask >= 0.10
Requires:         python-eventlet >= 0.13.0
Requires:         python-iso8601 >= 0.1.9
Requires:         python-kombu >= 2.4.8
Requires:         python-oslo-config >= 1.4.0.0a3
Requires:         python-oslo-messaging >= 1.4.0.0a3
Requires:         python-posix_ipc
Requires:         python-novaclient >= 2.17.0
Requires:         python-netaddr >= 0.7.6
Requires:         python-keystoneclient >= 0.10.0
Requires:         python-pecan >= 0.4.5
Requires:         python-routes >= 1.12.3
Requires:         python-sqlalchemy >= 0.9.7
Requires:         python-stevedore >= 0.14
Requires:         python-webob >= 1.2.3
Requires:         python-wsme >= 0.6

%if 0%{?rhel} == 6
Requires(post):   chkconfig
Requires(postun): initscripts
Requires(preun):  chkconfig
Requires(preun):  initscripts
# for daemon_notify
Requires: /usr/bin/uuidgen
Requires: /bin/sleep
%else
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
BuildRequires: systemd
%endif
Requires(pre):    shadow-utils

%description
OpenStack Reservation-as-a-Service (codename Blazar) is open source software
aiming to allow the reservation of both virtual and physical resources in a
calendar based on various reservation criteria.

This package contains the Blazar daemon.

%prep
%setup -q -n blazar-%{commit}

%patch0001 -p1
%patch0002 -p1

find . \( -name .gitignore -o -name .placeholder \) -delete

find blazar climate -name \*.py -exec sed -i '/\/usr\/bin\/env python/{d;q}' {} +

sed -i s/REDHATBLAZARVERSION/%{version}/ climate/version.py
sed -i s/REDHATBLAZARRELEASE/%{release}/ climate/version.py

# Let RPM handle the dependencies
rm -f test-requirements.txt requirements.txt

%build
cp etc/climate/climate.conf.sample etc/climate/climate.conf

PBR_VERSION=%{version} %{__python} setup.py build

%install
PBR_VERSION=%{version} %{__python} setup.py install --skip-build --root %{buildroot}

# Delete tests
rm -fr %{buildroot}%{python_sitelib}/climate/tests

install -d -m 755 %{buildroot}%{_sysconfdir}/climate
install -p -D -m 640 etc/climate/climate.conf %{buildroot}%{_sysconfdir}/climate/climate.conf
install -p -D -m 640 etc/policy.json %{buildroot}%{_sysconfdir}/climate/policy.json
install -p -D -m 644 %{SOURCE1} %{buildroot}%{_sysconfdir}/logrotate.d/openstack-blazar
%if 0%{?rhel} == 6
# Install service readiness wrapper
%else
install -p -D -m 755 %{SOURCE10} %{buildroot}%{_unitdir}/openstack-blazar-api.service
install -p -D -m 755 %{SOURCE11} %{buildroot}%{_unitdir}/openstack-blazar-manager.service
%endif

install -d -m 755 %{buildroot}%{_sharedstatedir}/climate
install -d -m 755 %{buildroot}%{_localstatedir}/log/climate
%if 0%{?rhel} == 6
install -d -m 755 %{buildroot}%{_localstatedir}/run/climate
%endif

%pre
getent group climate >/dev/null || groupadd -r climate
getent passwd climate >/dev/null || \
useradd -r -g climate -d %{_sharedstatedir}/climate -s /sbin/nologin \
-c "OpenStack Blazar Daemons" climate
exit 0

%post
%if 0%{?rhel} == 6
if [ $1 -eq 1 ] ; then
    # Initial installation
    /sbin/chkconfig --add openstack-blazar
fi
%else
%systemd_post openstack-blazar-api.service
%systemd_post openstack-blazar-manager.service
%endif

%preun
%if 0%{?rhel} == 6
if [ $1 -eq 0 ] ; then
    # Package removal, not upgrade
    /sbin/service openstack-blazar stop >/dev/null 2>&1
    /sbin/chkconfig --del openstack-blazar
fi
%else
%systemd_preun openstack-blazar-api.service
%systemd_preun openstack-blazar-manager.service
%endif

%postun
%if 0%{?rhel} == 6
if [ $1 -ge 1 ] ; then
    # Package upgrade, not uninstall
    /sbin/service openstack-blazar condrestart >/dev/null 2>&1 || :
fi
%else
%systemd_postun_with_restart openstack-blazar-api.service
%systemd_postun_with_restart openstack-blazar-manager.service
%endif

%files
%{_bindir}/blazar-api
%{_bindir}/blazar-db-manage
%{_bindir}/blazar-manager
%{_bindir}/blazar-rpc-zmq-receiver
%{_bindir}/climate-api
%{_bindir}/climate-db-manage
%{_bindir}/climate-manager
%{_bindir}/climate-rpc-zmq-receiver
%doc LICENSE
%doc README.rst
%if 0%{?rhel} == 6
%attr(0755, root, root) %{_datadir}/blazar/daemon_notify.sh
%{_datadir}/blazar/%{name}.upstart
%{_initrddir}/openstack-blazar
%else
%{_unitdir}/openstack-blazar-api.service
%{_unitdir}/openstack-blazar-manager.service
%endif
%dir %attr(0750, root, climate) %{_sysconfdir}/climate
%config(noreplace) %attr(0640, root, climate) %{_sysconfdir}/climate/climate.conf
%config(noreplace) %attr(0640, climate, climate) %{_sysconfdir}/climate/policy.json
%config(noreplace) %{_sysconfdir}/logrotate.d/openstack-blazar
%dir %attr(-, climate, climate) %{_sharedstatedir}/climate
%dir %attr(0750, climate, climate) %{_localstatedir}/log/climate
%if 0%{?rhel} == 6
%dir %attr(-, climate, climate) %{_localstatedir}/run/climate
%endif
%{python_sitelib}/climate
%{python_sitelib}/blazar-%{version}-*.egg-info


%changelog
* Thu Jan 22 2015 Pierre Riteau <priteau@uchicago.edu> 2014.2.1-1.gite84096852f17ec14feb9b600ba5a07174fdab7ec
- Initial packaging
