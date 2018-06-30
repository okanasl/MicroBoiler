// Copyright (c) Brock Allen & Dominick Baier. All rights reserved.
// Licensed under the Apache License, Version 2.0. See LICENSE in the project root for license information.


using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using System;
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
using MassTransit;
using MassTransit.ExtensionsDependencyInjectionIntegration;

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

            var migrationsAssembly = typeof(Startup).GetTypeInfo().Assembly.GetName().Name;
            
//& region (database)
            const string userconnectionString = @"{{database:usersconnectionstring}}";
            const string connectionString = @"{{database:configconnectionstring}}";
    //& region (mssql)
            services.AddDbContext<UserDbContext>(options =>
                options.UseSqlServer(userconnectionString)
                );
    //& endregion (mssql)
    //& region (mysql)
            services.AddDbContext<UserDbContext>(options =>
                options.UseMySql(userconnectionString)
                );
    //& endregion (mysql)
    //& region (postgresql)
            services.AddDbContext<UserDbContext>(options =>
                options.UseNpgsql(userconnectionString)
                );
    //& endregion (postgresql)
//& endregion (database)
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
    //& region (mssql)
                        builder.UseSqlServer(connectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));                    
    //& endregion (mssql)
    //& region (postgresql)
                        builder.UseNpgsql(connectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));                    
    //& endregion (postgresql)
    //& region (mysql)
                        builder.UseMySql(connectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));                    
    //& endregion (mysql)
//& endregion (database)
                    };
                })
                // this adds the operational data from DB (codes, tokens, consents)
                .AddOperationalStore(options =>
                {
//& region (database)
    //& region (mssql)
                    options.ConfigureDbContext = builder =>
                        builder.UseSqlServer(connectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));
    //& endregion (mssql)
    //& region (postgresql)
                    options.ConfigureDbContext = builder =>
                        builder.UseNpgsql(connectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));
    //& endregion (postgresql)
    //& region (mysql)
                    options.ConfigureDbContext = builder =>
                        builder.UseMySql(connectionString,
                            sql => sql.MigrationsAssembly(migrationsAssembly));
    //& endregion (mysql)
//& region (database)
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
            services.AddSingleton(provider => Bus.Factory.CreateUsingRabbitMq(cfg =>
            {
                var host = cfg.Host("localhost", "/", h => {
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
            }));

            services.AddSingleton<IPublishEndpoint>(provider => provider.GetRequiredService<IBusControl>());
            services.AddSingleton<ISendEndpointProvider>(provider => provider.GetRequiredService<IBusControl>());
            services.AddSingleton<IBus>(provider => provider.GetRequiredService<IBusControl>());
            // Register with IHostedService To Start bus in Application Start
            services.AddSingleton<Microsoft.Extensions.Hosting.IHostedService, BusService>();
    //& endregion (eventbus:rabbitmq)
//& endregion (eventbus)
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

        public void Configure(IApplicationBuilder app, IHostingEnvironment env
//& region (logging)
            ,ILoggerFactory loggerFactory
//& endregion (logging)
        )
        {
//& region (logging)
            loggerFactory.AddConsole(_config.GetSection("Logging"));
            loggerFactory.AddDebug();
//& endregion (logging)
            if (env.IsDevelopment())
            {
                app.UseDeveloperExceptionPage();
                app.UseDatabaseErrorPage();
            }
            else
            {
                
                app.UseExceptionHandler("/Home/Error");
            }

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
