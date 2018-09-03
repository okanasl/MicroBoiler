// Copyright (c) Brock Allen & Dominick Baier. All rights reserved.
// Licensed under the Apache License, Version 2.0. See LICENSE in the project root for license information.

using System;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using IdentityServer4.Quickstart.UI;
using Microsoft.Extensions.Configuration;
using Microsoft.AspNetCore.Localization;
using Microsoft.EntityFrameworkCore;
using System.Reflection;
using Microsoft.AspNetCore.Hosting;
using Host.Models;
using Microsoft.AspNetCore.Identity;
using IdentityServer4.AspNetIdentity;
using Host.Localization;
using Microsoft.AspNetCore.Mvc.Razor;
using System.Globalization;
using System.Collections.Generic;
using Host.Services;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.Logging;
using IdentityServer4.EntityFramework;
using IdentityServer4.EntityFramework.DbContexts;
using IdentityServer4.Entities;
using IdentityServer4.EntityFramework.UserContext;
using IdentityServer4;
//& region (eventbus)
using MassTransit;
using MassTransit.ExtensionsDependencyInjectionIntegration;
using Polly;
//& end (eventbus)

//& region (server)
using Microsoft.AspNetCore.HttpOverrides;
using Polly.Retry;
using System.Net.Sockets;
using RabbitMQ.Client.Exceptions;
using MassTransit.RabbitMqTransport;
//& end (server)

namespace Host
{
    public class Startup
    {
        private readonly IConfiguration _config;
        private readonly IHostingEnvironment _env;

        public Startup(IConfiguration config, IHostingEnvironment env)
        {
            _config = config;
            _env = env;
        }

        public IServiceProvider ConfigureServices(IServiceCollection services)
        {
            string env = Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT");
            //& region (database)
            string configsConnectionString;  
            string usersConnectionString; 
            //& end (database)  
            //& region (eventbus)
            //& region (eventbus:rabbitmq)
            string rabbitHostString;
            //& end (eventbus:rabbitmq)
            //& end (eventbus)
            if (env == "Development")
            {
            //& region (database)
                usersConnectionString = "{{database:usersconnectionstring-dev}}";
                configsConnectionString= "{{database:configsConnectionString-dev}}";  
            //& end (database)  
            //& region (eventbus)
            //& region (eventbus:rabbitmq)
                rabbitHostString = "{{rabbitmq:host-dev}}";
            //& end (eventbus:rabbitmq)
            //& end (eventbus)
            }
            else // if (env == "Docker_Production")
            {
            //& region (database)
                usersConnectionString = "{{database:usersconnectionstring}}";
                configsConnectionString= "{{database:configsConnectionString}}";  
            //& end (database)  
            //& region (eventbus)
            //& region (eventbus:rabbitmq)
                rabbitHostString = "{{rabbitmq:host}}";
            //& end (eventbus:rabbitmq)
            //& end (eventbus)
            }
            var migrationsAssembly = typeof(Startup).GetTypeInfo().Assembly.GetName().Name;
            
//& region (database)
//& region (database:mssql)
            services.AddDbContext<UserDbContext>(options =>
                options.UseSqlServer(usersConnectionString,
                    sql => sql.MigrationsAssembly(migrationsAssembly))
                );
//& end (database:mssql)
//& region (database:mysql)
            services.AddDbContext<UserDbContext>(options =>
                options.UseMySql(usersConnectionString,
                    sql => sql.MigrationsAssembly(migrationsAssembly))
                );
//& end (database:mysql)
//& region (database:postgresql)
            services.AddDbContext<UserDbContext>(options =>
                options.UseNpgsql(usersConnectionString,
                    sql => sql.MigrationsAssembly(migrationsAssembly))
                );
//& end (database:postgresql)
//& end (database)
            services.AddIdentity<ApplicationUser, ApplicationRole>()
                .AddEntityFrameworkStores<UserDbContext>();            
            
            services.AddTransient<IEmailSender, AuthMessageSender>();
            services.AddTransient<ISmsSender, AuthMessageSender>();

            services.AddIdentityServer(options =>
                {
                    options.Events.RaiseSuccessEvents = true;
                    options.Events.RaiseFailureEvents = true;
                    options.Events.RaiseErrorEvents = true;
                    options.Events.RaiseInformationEvents = true;                    
                })
                .AddDeveloperSigningCredential()
                // .AddTestUsers(TestUsers.Users)
                .AddAspNetIdentity<ApplicationUser>()
                // You can Configure Profile Service for your needs
                .AddProfileService<AuthProfileService>()
                // this adds the config data from DB (clients, resources, CORS)
                .AddConfigurationStore(options =>
                {
                    options.ResolveDbContextOptions = (provider, builder) =>
                    {
//& region (database)
//& region (database:postgresql)
                        builder.UseNpgsql(configsConnectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));                    
//& end (database:postgresql)
//& region (database:mysql)
                        builder.UseMySql(configsConnectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));                    
//& end (database:mysql)
//& region (database:mssql)
                        builder.UseSqlServer(configsConnectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));                    
//& end (database:mssql)
//& end (database)
                    };
                })
                // this adds the operational data from DB (codes, tokens, consents)
                .AddOperationalStore(options =>
                {
                    options.ConfigureDbContext = (builder) =>
                    {
//& region (database)
    //& region (database:mssql)
                        builder.UseSqlServer(configsConnectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));
//& end (database:mssql)
//& region (database:postgresql)
                        builder.UseNpgsql(configsConnectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));
//& end (database:postgresql)
//& region (database:mysql)
                        builder.UseMySql(configsConnectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));
//& end (database:mysql)
//& region (database)
                    };
                    // this enables automatic token cleanup. this is optional.
                    options.EnableTokenCleanup = true;
                    // options.TokenCleanupInterval = 10; // interval in seconds, short for testing
                })
                .AddConfigurationStoreCache();



//& region (eventbus)
//& region (eventbus:rabbitmq)
            services.AddMassTransit(p=>{
                // p.AddConsumer<SomeEventHappenedConsumer>();
            });            
            var _retryCount = 8;
            var policy = RetryPolicy.Handle<SocketException>()
                .Or<BrokerUnreachableException>()
                .Or<RabbitMqConnectionException>()
                .OrInner<BrokerUnreachableException>()
                .OrInner<RabbitMqConnectionException>()
                .WaitAndRetry(_retryCount, retryAttempt => TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)), (ex, time) =>
                {
                    Console.WriteLine("Could not connect Broker Trying Again");
                    Console.WriteLine(ex);
                    Console.WriteLine("Retrying RabbitMq Connection");
                }
            );
            IServiceProvider prov = services.BuildServiceProvider();
            IBusControl busControl;
            policy.Execute(() =>
            {
                busControl = Bus.Factory.CreateUsingRabbitMq(cfg =>
                {
                    var host = cfg.Host(new Uri(rabbitHostString), "/", h => {
                        h.Username("{{rabbitmq:user:username}}");
                        h.Password("{{rabbitmq:user:password}}");
                    });

                    cfg.ReceiveEndpoint(host, e =>
                    {
                        e.PrefetchCount = 8;
                        // Add Your Event Consumers Here
                        // If you want Inject services to consumer, pass provider param
                        // e.Consumer<SomeEventHappenedConsumer>(provider)
                    });
                });
                services.AddSingleton(provider => busControl);
            });
            services.AddSingleton<IPublishEndpoint>(provider => provider.GetRequiredService<IBusControl>());
            services.AddSingleton<ISendEndpointProvider>(provider => provider.GetRequiredService<IBusControl>());
            services.AddSingleton<IBus>(provider => provider.GetRequiredService<IBusControl>());
            // Register with IHostedService To Start bus in Application Start
            services.AddSingleton<Microsoft.Extensions.Hosting.IHostedService, BusService>();
//& end (eventbus:rabbitmq)
//& end (eventbus)
            services.AddSingleton<LocService>();
            services.AddLocalization(options => options.ResourcesPath = "Resources");
            services.AddScoped<ClientIdFilter>();
            services.AddScoped<ClientSelector>();

            services.Configure<RazorViewEngineOptions>(options =>
            {
                options.ViewLocationExpanders.Add(new ClientViewLocationExpander());
            });

            services.Configure<RequestLocalizationOptions>(
            options =>
            {
                var supportedCultures = new List<CultureInfo>
                    {
                        new CultureInfo("en-US"),
                        new CultureInfo("de-CH"),
                        new CultureInfo("fr-CH")
                    };

                options.DefaultRequestCulture = new RequestCulture(culture: "en-US", uiCulture: "en-US");
                options.SupportedCultures = supportedCultures;
                options.SupportedUICultures = supportedCultures;

                var providerQuery = new LocalizationQueryProvider
                {
                    QureyParamterName = "ui_locales"
                };

                // Cookie is required for the logout, query parameters at not supported with the endsession endpoint
                // Only works in the same domain
                var providerCookie = new LocalizationCookieProvider
                {
                    CookieName = "defaultLocale"
                };
                // options.RequestCultureProviders.Insert(0, providerCookie);
                options.RequestCultureProviders.Insert(0, providerQuery);
            });
            
            services.AddMvc()
                .AddViewLocalization()
                .AddDataAnnotationsLocalization(options =>
                {
                    options.DataAnnotationLocalizerProvider = (type, factory) =>
                    {
                        var assemblyName = new AssemblyName(typeof(SharedResource).GetTypeInfo().Assembly.FullName);
                        return factory.Create("SharedResource", assemblyName.Name);
                    };
                });

            return services.BuildServiceProvider(validateScopes: false);
        }

        public void Configure(
            IApplicationBuilder app,
            IHostingEnvironment env
//& region (logging)
            ,ILoggerFactory loggerFactory
//& end (logging)
        )
        {
//& region (logging)
            loggerFactory.AddConsole(_config.GetSection("Logging"));
            loggerFactory.AddDebug();
//& end (logging)
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
                app.UseDatabaseErrorPage();
            }
            else
            {                
                app.UseExceptionHandler("/Home/Error");
            }
//& region (server)
            app.UseForwardedHeaders(new ForwardedHeadersOptions
            {
                ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto
            });
//& end (server)
            var locOptions = app.ApplicationServices.GetService<IOptions<RequestLocalizationOptions>>();
            app.UseRequestLocalization(locOptions.Value);


            app.UseStaticFiles();

            app.UseIdentityServer();

            app.UseMvc(routes =>
            {
                routes.MapRoute(
                    name: "default",
                    template: "{controller=Home}/{action=Index}/{id?}");
            });
 
        }
    }
}
