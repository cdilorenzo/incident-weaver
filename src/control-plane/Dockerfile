FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY src/control-plane/ControlPlane.csproj src/control-plane/
RUN dotnet restore src/control-plane/ControlPlane.csproj
COPY src/control-plane/ src/control-plane/
RUN dotnet publish src/control-plane/ControlPlane.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/publish .
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "ControlPlane.dll"]