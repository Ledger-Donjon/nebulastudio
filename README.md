# NebulaStudio

NebulaStudio is a project designed to observe and exploit the results of differential images. This repository contains the source code and documentation for the NebulaStudio application.

## Features

- Feature 1: Import several images to be visualized side by side with synchronized zooming and panning
- Feature 2: Have synchronized reticulas over all the images to point out the same position on all images
- Feature 3: Possibility to fix the reticulas

## Installation

To get started with NebulaStudio, follow these steps:

1. Recommended: Create a virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install Nebula Studio with `pip` directly from git repository:

   ```bash
   python3 -m pip install git+https://github.com/Ledger-Donjon/nebulastudio.git
   ```

   or from `pypi`:

   ```bash
   python3 -m pip install donjon-nebulastudio
   ```

## Usage

Run the application with the following command:

```bash
nebulastudio
```

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add feature-name"
   ```
4. Push to your branch:
   ```bash
   git push origin feature-name
   ```
5. Open a pull request.

## License

This project is licensed under the _LGPL-3.0_ License. See the [LICENSE](./LICENSE) file for details.
