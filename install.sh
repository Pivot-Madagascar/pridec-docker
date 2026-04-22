#!/bin/bash

#pull image
echo "Pulling pridec docker image. This will download a 3 GB image."
docker compose --file compose.yaml build


#create symlink to run app anywhere
chmod +x ./pridec
mkdir -p "$HOME/bin"
ln -sf "$(pwd)/pridec" "$HOME/bin/pridec"
echo "Installed symlink: $HOME/bin/pridec -> $(pwd)/pridec"

case ":$PATH:" in
  *":$HOME/bin:"*)
    echo "$HOME/bin is already in your PATH."
    ;;
  *)
    echo "$HOME/bin is not in your PATH."
    echo "   Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"\$HOME/bin:\$PATH\""
    ;;
esac

echo "SUCCESS: PRIDE-C app is now available via pridec run <service-name>"
echo "Available services: etl, forecast"