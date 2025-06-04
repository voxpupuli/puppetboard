# How to release

## On a fork do

```shell
git switch -c release-x.y.z
```

Edit [pyproject.toml](pyproject.toml) and set future version.  With uv locally, you can also do `uv version --bump <patch, minor, major, prepatch, preminor, premajor, prerelease>` to automatically update.

```shell
bundle config set --local path .vendor
bundle config set --local with 'release'
bundle install

CHANGELOG_GITHUB_TOKEN="token_MC_token-face" bundle exec rake changelog
git add -A
git commit -m 'Release X.Y.Z'
git push origin releae-x.y.z
```

## as a maintainer on upstream do

```shell
git switch master
git pull
git tag $version
git push --tags
```
