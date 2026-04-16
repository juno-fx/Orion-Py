When working on this repo, make sure to:

- This is orionpy, a Python library for Kubernetes service-to-service authentication
- The main implementation is in `orionpy/network/orionrequests.py` which provides the OrionRequests client
- OrionRequests automatically manages service account tokens for authenticated requests between services
- Tokens are cached and automatically refreshed when they expire in < 5 minutes
- The testservice in `test-service/` is a simple HTTP service used for testing that validates auth via rhea sidecar
- E2E tests go in `tests/test_e2e_*.py` and run against deployed services in the cluster
- Unit tests go in `tests/test_*.py` and use mocks to test individual components
- Cedar policies in `k8s/testservice/rhea.configmap.yaml` control access to services
- Validate all changes in this order: first run make lint, then run unittests, then e2e tests
- Run `make test-unit` for unit tests only, `make test` for full e2e tests
- Tests use pytest with coverage reporting
