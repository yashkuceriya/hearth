FROM ruby:3.3-slim AS builder
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle config set --local deployment true && bundle install --jobs 4

FROM ruby:3.3-slim
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/* && \
    groupadd -r appuser && useradd -r -g appuser -u 1000 appuser
WORKDIR /app
COPY --from=builder /app/vendor /app/vendor
COPY --from=builder /usr/local/bundle /usr/local/bundle
COPY . .
ENV BUNDLE_DEPLOYMENT=true
USER appuser
EXPOSE 50055 8084
ENTRYPOINT ["bundle", "exec", "ruby", "lib/server.rb"]
