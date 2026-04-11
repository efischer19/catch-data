# Reusable Terraform Modules

This directory contains reusable Terraform modules for common infrastructure
patterns. Each module should be a self-contained directory with its own
`main.tf`, `variables.tf`, and `outputs.tf`.

## Creating a Module

```text
modules/
└── my-module/
    ├── main.tf        # Resource definitions
    ├── variables.tf   # Input variables
    ├── outputs.tf     # Output values
    └── README.md      # Module documentation
```

## Usage

Reference modules from the root `infrastructure/main.tf`:

```hcl
module "my_module" {
  source      = "./modules/my-module"
  environment = var.environment
}
```

See the [Terraform modules documentation](https://developer.hashicorp.com/terraform/language/modules)
for best practices.
