#region (build_dev)
FROM microsoft/dotnet:2.1-sdk-alpine AS build
# Set the working directory witin the container
WORKDIR /src

# Copy all of the source files
COPY * ./

# Restore all packages
RUN dotnet restore ./IdentityService/Host/Host.csproj

# Build the source code
RUN dotnet build ./IdentityService/Host/Host.csproj

# Ensure that we generate and migrate the database
RUN bash migrations.sh
RUN bash updatedb.sh

# Publish application
WORKDIR ..
RUN dotnet publish ./Host/Host.csproj --output "../../dist"

# Build runtime image
FROM microsoft/dotnet:2.1-aspnetcore-runtime-alpine AS app
WORKDIR /app
COPY --from=build /dist .
ENV ASPNETCORE_URLS http://+:{{port}}

ENTRYPOINT ["dotnet", "Host.dll"]

#endregion