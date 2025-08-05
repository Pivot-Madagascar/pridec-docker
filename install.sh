#!/bin/bash

#build image
echo "Building pridec docker image. This will take 15 minutes"
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