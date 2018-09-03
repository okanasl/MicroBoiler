#!/bin/sh
cd src
rm -rf Migrations

dotnet ef migrations add InitialMigrations -c {{DatabaseContextName}} -o Migrations/IdentityServer/UsersDb
dotnet ef migrations script -c {{DatabaseContextName}} -o Migrations/{{ProjectName}}/{{DatabaseContextName}}.sql
cd ..
