FROM node:20-alpine
WORKDIR /app

# Install Jest from package.json
COPY package.json ./
RUN npm install --no-progress --quiet

# Copy source and tests
COPY src/   ./src/
COPY tests/js/ ./tests/js/

CMD ["npm", "test", "--", "--coverage", "--coverageDirectory=/reports/server-js"]
