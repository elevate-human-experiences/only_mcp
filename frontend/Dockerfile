# Dev stage: For development purposes
FROM node:23-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
    EXPOSE 4096
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
