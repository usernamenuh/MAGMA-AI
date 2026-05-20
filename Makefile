.PHONY: rebuild

rebuild:
	sed -i "s|^Image=.*|Image=$(IMAGE)|" /etc/containers/systemd/$(SERVICE).container
	systemctl daemon-reload
	systemctl restart $(SERVICE)
